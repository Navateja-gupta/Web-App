from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AuthenticationError, BusinessRuleError, ConflictError, PermissionDeniedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    spend_password_check_time,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import RefreshToken, User
from app.schemas.user import PasswordChange, UserRegister, UserUpdate
from app.services.audit import record_audit

INVALID_CREDENTIALS = "Incorrect email or password"
SESSION_EXPIRED = "Your session has expired. Please log in again."
# A refresh token reused within this window is treated as a harmless race (two tabs refreshing
# at once) rather than theft.
REUSE_GRACE = timedelta(seconds=30)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def register_user(db: Session, data: UserRegister) -> User:
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise ConflictError("An account with this email already exists")
    if data.phone and db.scalar(select(User.id).where(User.phone == data.phone)):
        raise ConflictError("An account with this phone number already exists")

    user = User(
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=UserRole(data.role),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        # Lost a race with a concurrent registration using the same email/phone.
        db.rollback()
        raise ConflictError("An account with these details already exists")

    record_audit(db, actor_id=user.id, action="user.registered", entity_type="user", entity_id=user.id,
                 details={"role": user.role.value})
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        spend_password_check_time(password)
        raise AuthenticationError(INVALID_CREDENTIALS)

    valid, upgraded_hash = verify_password(password, user.password_hash)
    if not valid:
        raise AuthenticationError(INVALID_CREDENTIALS)
    if not user.is_active:
        raise PermissionDeniedError("This account has been deactivated. Please contact support.")

    if upgraded_hash:
        user.password_hash = upgraded_hash
    user.last_login_at = _now()
    db.commit()
    return user


def issue_session(db: Session, user: User) -> tuple[str, str]:
    """Create a new access token and a new stored refresh token. Returns (access, refresh)."""
    refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    return create_access_token(user.id, user.role.value), refresh


def rotate_refresh_token(db: Session, raw_token: str | None) -> tuple[User, str, str]:
    """Exchange a valid refresh token for a new pair. The old refresh token is revoked."""
    if not raw_token:
        raise AuthenticationError(SESSION_EXPIRED)

    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token)).with_for_update()
    )
    if stored is None:
        raise AuthenticationError(SESSION_EXPIRED)

    now = _now()
    if stored.revoked_at is not None:
        if now - stored.revoked_at > REUSE_GRACE:
            # An old token was replayed: possible theft, so end every session of this user.
            revoke_all_sessions(db, stored.user_id)
            record_audit(db, actor_id=stored.user_id, action="auth.refresh_token_reuse",
                         entity_type="user", entity_id=stored.user_id)
            db.commit()
        raise AuthenticationError(SESSION_EXPIRED)

    if stored.expires_at <= now:
        raise AuthenticationError(SESSION_EXPIRED)

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError(SESSION_EXPIRED)

    stored.revoked_at = now
    access, refresh = issue_session(db, user)
    return user, access, refresh


def revoke_refresh_token(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw_token), RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    db.commit()


def revoke_all_sessions(db: Session, user_id: int) -> None:
    """Revoke every refresh token of a user and invalidate their outstanding access tokens.

    Does not commit; callers commit as part of their own transaction.
    """
    now = _now()
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.execute(update(User).where(User.id == user_id).values(tokens_valid_after=now))


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    changes = data.model_dump(exclude_unset=True)
    if "full_name" in changes and changes["full_name"] is None:
        raise BusinessRuleError("Name cannot be empty")
    if "email_notifications" in changes and changes["email_notifications"] is None:
        changes.pop("email_notifications")
    new_phone = changes.get("phone")
    if new_phone and new_phone != user.phone:
        if db.scalar(select(User.id).where(User.phone == new_phone, User.id != user.id)):
            raise ConflictError("An account with this phone number already exists")

    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, data: PasswordChange) -> None:
    valid, _ = verify_password(data.current_password, user.password_hash)
    if not valid:
        raise BusinessRuleError("Current password is incorrect")
    if data.current_password == data.new_password:
        raise BusinessRuleError("New password must be different from the current password")

    user.password_hash = hash_password(data.new_password)
    revoke_all_sessions(db, user.id)
    record_audit(db, actor_id=user.id, action="user.password_changed", entity_type="user", entity_id=user.id)
    db.commit()
    db.refresh(user)
