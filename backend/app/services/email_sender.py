"""Deliver queued emails over SMTP (e.g. Gmail with an app password).

A background thread started with the app calls `process_outbox()` every few seconds.
Rows are locked with SKIP LOCKED, so several server processes never send the same email twice.
"""

import logging
import smtplib
import ssl
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.enums import EmailStatus
from app.models.notification import EmailOutbox

logger = logging.getLogger(__name__)

Sender = Callable[[str, str, str], None]


def smtp_send(to_email: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.email_from_address))
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()
    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=20) as smtp:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD.replace(" ", ""))
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as smtp:
            smtp.starttls(context=context)
            # Gmail shows app passwords with spaces; they are not part of the password.
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD.replace(" ", ""))
            smtp.send_message(message)


def _safe_error(exc: Exception) -> str:
    # Never store the password; SMTP errors do not include it, but keep messages short.
    return f"{type(exc).__name__}: {exc}"[:500]


def process_outbox(db: Session, sender: Sender = smtp_send, *, ids: list[int] | None = None, batch: int = 20) -> int:
    """Send pending emails. Returns how many were sent successfully."""
    stmt = (
        select(EmailOutbox)
        .where(EmailOutbox.status == EmailStatus.PENDING, EmailOutbox.attempts < settings.EMAIL_MAX_ATTEMPTS)
        .order_by(EmailOutbox.id)
        .limit(batch)
        .with_for_update(skip_locked=True)
    )
    if ids is not None:
        stmt = stmt.where(EmailOutbox.id.in_(ids))

    sent = 0
    for email in db.scalars(stmt).all():
        try:
            sender(email.to_email, email.subject, email.body)
        except Exception as exc:  # network, auth, recipient refused...
            email.attempts += 1
            email.last_error = _safe_error(exc)
            if email.attempts >= settings.EMAIL_MAX_ATTEMPTS:
                email.status = EmailStatus.FAILED
            logger.warning("Email %s to %s failed (attempt %s): %s", email.id, email.to_email, email.attempts, email.last_error)
        else:
            email.attempts += 1
            email.status = EmailStatus.SENT
            email.sent_at = datetime.now(timezone.utc)
            email.last_error = None
            sent += 1
        db.commit()
    return sent


def outbox_counts(db: Session) -> dict[str, int]:
    counts = {status.value: 0 for status in EmailStatus}
    for status, count in db.execute(select(EmailOutbox.status, func.count()).group_by(EmailOutbox.status)).all():
        counts[status.value] = count
    return counts


class OutboxWorker:
    """Background thread that keeps the outbox moving while the API is running."""

    def __init__(self, interval_seconds: int) -> None:
        self.interval = interval_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="email-outbox", daemon=True)

    def start(self) -> None:
        logger.info("Email outbox worker started (every %ss)", self.interval)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                with SessionLocal() as db:
                    process_outbox(db)
            except Exception:
                logger.exception("Email outbox worker error")
