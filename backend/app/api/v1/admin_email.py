from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BusinessRuleError
from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models.enums import EmailStatus
from app.models.notification import EmailOutbox
from app.models.user import User
from app.services import email_sender
from app.services.notifications import render_email

router = APIRouter(prefix="/admin/email", tags=["admin: email"])


class FailedEmail(BaseModel):
    to_email: str
    subject: str
    last_error: str | None
    attempts: int
    created_at: datetime


class EmailStatusRead(BaseModel):
    enabled: bool
    configured: bool
    from_address: str
    smtp_host: str
    counts: dict[str, int]
    recent_failures: list[FailedEmail]


class TestEmailResult(BaseModel):
    status: EmailStatus
    to_email: str
    error: str | None


def get_email_sender() -> email_sender.Sender:
    """Dependency so tests can replace real SMTP."""
    return email_sender.smtp_send


@router.get("/status", response_model=EmailStatusRead)
def email_status(_admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> EmailStatusRead:
    failures = db.scalars(
        select(EmailOutbox)
        .where(EmailOutbox.last_error.is_not(None), EmailOutbox.status != EmailStatus.SENT)
        .order_by(EmailOutbox.id.desc())
        .limit(5)
    ).all()
    return EmailStatusRead(
        enabled=settings.EMAIL_ENABLED,
        configured=settings.email_configured,
        from_address=settings.email_from_address,
        smtp_host=settings.SMTP_HOST,
        counts=email_sender.outbox_counts(db),
        recent_failures=[FailedEmail.model_validate(f, from_attributes=True) for f in failures],
    )


@router.post("/test", response_model=TestEmailResult)
def send_test_email(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    sender: email_sender.Sender = Depends(get_email_sender),
) -> TestEmailResult:
    """Send a test email to your own address right now and report the result."""
    if not settings.EMAIL_ENABLED:
        raise BusinessRuleError("Email is turned off. Set EMAIL_ENABLED=true in backend/.env and restart the API.")
    if not settings.email_configured:
        raise BusinessRuleError("SMTP_USERNAME and SMTP_PASSWORD are not set in backend/.env.")

    email = EmailOutbox(
        user_id=admin.id,
        to_email=admin.email,
        subject="Test email from Kamareddy Wedding Services",
        body=render_email(admin, "This is a test. If you can read this, email notifications are working.", "/admin/overview"),
    )
    db.add(email)
    db.commit()
    email_sender.process_outbox(db, sender, ids=[email.id])
    db.refresh(email)
    return TestEmailResult(status=email.status, to_email=email.to_email, error=email.last_error)
