"""Admin-assisted password reset.

An administrator generates a one-time link and shares it directly with the user
(phone/WhatsApp). The token lives in the URL fragment (#token=...), which browsers
never send to servers, and only its SHA-256 hash is stored.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BusinessRuleError, NotFoundError
from app.core.security import hash_password, hash_token
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.audit import record_audit
from app.services.auth import revoke_all_sessions
from app.services.notifications import notify

INVALID_LINK = "This reset link is invalid, already used or expired. Ask the administrator for a new one."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_reset_link(db: Session, admin: User, user_id: int) -> tuple[str, datetime, User]:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.id == admin.id:
        raise BusinessRuleError("Use Account → Change password for your own account")
    if not user.is_active:
        raise BusinessRuleError("Activate this account before resetting its password")

    now = _now()
    # Only the newest link works: cancel any earlier unused ones.
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw = secrets.token_urlsafe(32)
    expires_at = now + timedelta(hours=settings.PASSWORD_RESET_EXPIRE_HOURS)
    db.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(raw), expires_at=expires_at, created_by_id=admin.id))
    record_audit(db, actor_id=admin.id, action="user.password_reset_link_created", entity_type="user", entity_id=user.id)
    db.commit()

    url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password#token={raw}"
    return url, expires_at, user


def _usable_token(db: Session, raw: str, *, lock: bool = False) -> PasswordResetToken:
    stmt = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == hash_token(raw),
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > _now(),
    )
    if lock:
        stmt = stmt.with_for_update()
    token = db.scalar(stmt.execution_options(populate_existing=True))
    if token is None:
        raise BusinessRuleError(INVALID_LINK)
    return token


def check_link(db: Session, raw: str) -> User:
    user = db.get(User, _usable_token(db, raw).user_id)
    if user is None or not user.is_active:
        raise BusinessRuleError(INVALID_LINK)
    return user


def reset_password(db: Session, raw: str, new_password: str) -> None:
    token = _usable_token(db, raw, lock=True)
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise BusinessRuleError(INVALID_LINK)

    user.password_hash = hash_password(new_password)
    token.used_at = _now()
    revoke_all_sessions(db, user.id)  # sign out everywhere, including whoever knew the old password
    record_audit(db, actor_id=user.id, action="user.password_reset", entity_type="user", entity_id=user.id)
    notify(
        db,
        [user],
        kind="account.password_reset",
        title="Your password was changed",
        body="Your password was reset using a reset link. If this wasn't you, contact the administrator immediately.",
        link="/account",
    )
    db.commit()
