"""In-app notifications + queued emails.

`notify()` only adds rows to the current transaction; the caller's commit makes the
business change, the notification and the email all-or-nothing. Emails are delivered
later by `email_sender.process_outbox()`.
"""

from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import NotFoundError
from app.dependencies.pagination import PageParams
from app.models.enums import EmailStatus, UserRole
from app.models.notification import EmailOutbox, Notification
from app.models.user import User


def _single_line(text: str, limit: int) -> str:
    """Email subjects must not contain line breaks (prevents header injection)."""
    return " ".join(text.split())[:limit]


def render_email(user: User, body: str, link: str | None) -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    parts = [f"Hello {user.full_name},", "", body]
    if link:
        parts += ["", f"Open: {base}{link}"]
    parts += [
        "",
        f"— {settings.EMAIL_FROM_NAME}",
        "",
        f"You receive these emails because email notifications are on. Turn them off in Account settings: {base}/account",
    ]
    return "\n".join(parts)


def notify(
    db: Session,
    recipients: Iterable[User],
    *,
    kind: str,
    title: str,
    body: str,
    link: str | None = None,
    email: bool = True,
) -> None:
    seen: set[int] = set()
    for user in recipients:
        if user is None or user.id in seen or not user.is_active:
            continue
        seen.add(user.id)
        db.add(Notification(user_id=user.id, kind=kind, title=_single_line(title, 200), body=body, link=link))
        if email and user.email_notifications:
            db.add(
                EmailOutbox(
                    user_id=user.id,
                    to_email=user.email,
                    subject=_single_line(title, 200),
                    body=render_email(user, body, link),
                    status=EmailStatus.PENDING if settings.EMAIL_ENABLED else EmailStatus.SKIPPED,
                )
            )


def active_admins(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True))))


# ---------- Reading notifications ----------

def list_notifications(
    db: Session, user: User, params: PageParams, *, unread_only: bool = False
) -> tuple[list[Notification], int]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).offset(params.offset).limit(params.size)
    ).all()
    return list(items), total


def unread_count(db: Session, user: User) -> int:
    return db.scalar(
        select(func.count()).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    ) or 0


def mark_read(db: Session, user: User, notification_id: int) -> Notification:
    notification = db.scalar(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
    )
    if notification is None:
        raise NotFoundError("Notification not found")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
    return notification


def mark_all_read(db: Session, user: User) -> int:
    result = db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    db.commit()
    return result.rowcount or 0
