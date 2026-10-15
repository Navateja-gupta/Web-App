from collections.abc import Callable
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.admin_email import get_email_sender
from app.core.config import settings
from app.main import app
from app.models.enums import ApprovalStatus, BookingStatus, EmailStatus, UserRole
from app.models.notification import EmailOutbox, Notification
from app.models.user import User
from app.services.email_sender import process_outbox
from app.services.notifications import notify
from tests.factories import make_booking, make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]
FUTURE = (date.today() + timedelta(days=40)).isoformat()


@pytest.fixture
def email_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "sender@example.com")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app password")


def notes_for(db: Session, user: User) -> list[Notification]:
    return list(db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.id)))


def emails_for(db: Session, user: User) -> list[EmailOutbox]:
    return list(db.scalars(select(EmailOutbox).where(EmailOutbox.user_id == user.id).order_by(EmailOutbox.id)))


def enquiry(vendor_id: int) -> dict[str, object]:
    return {"vendor_ids": [vendor_id], "service_date": FUTURE, "event_location": "Kamareddy hall",
            "requirements": "Full-day coverage for the wedding, please."}


# ---------- Who gets notified ----------

def test_enquiry_notifies_linked_vendor_by_app_and_email(email_on, client_for: ClientFor, db_session: Session) -> None:  # type: ignore[no-untyped-def]
    owner = make_user(db_session, role=UserRole.VENDOR)
    vendor = make_vendor(db_session, make_category(db_session), "Lens Studio", status=ApprovalStatus.APPROVED, owner=owner)
    customer = client_for(make_user(db_session, full_name="Anil Rao"))
    assert customer.post(f"{API}/me/quotation-requests", json=enquiry(vendor.id)).status_code == 201

    [note] = notes_for(db_session, owner)
    assert note.kind == "enquiry.created" and "Anil Rao" in note.body and note.link == "/vendor?tab=enquiries"
    [email] = emails_for(db_session, owner)
    assert email.status == EmailStatus.PENDING and email.to_email == owner.email
    assert f"{settings.FRONTEND_BASE_URL}/vendor?tab=enquiries" in email.body


def test_enquiry_for_vendor_without_login_goes_to_admins(client_for: ClientFor, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    vendor = make_vendor(db_session, make_category(db_session), "No Login Studio", status=ApprovalStatus.APPROVED)
    client_for(make_user(db_session)).post(f"{API}/me/quotation-requests", json=enquiry(vendor.id))
    [note] = notes_for(db_session, admin)
    assert note.title.startswith("[No vendor login]")
    assert vendor.contact_phone in note.body


def test_quotation_accept_and_confirm_notifications(client_for: ClientFor, db_session: Session) -> None:
    owner = make_user(db_session, role=UserRole.VENDOR)
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED, owner=owner)
    customer_user = make_user(db_session)
    customer, vendor_client = client_for(customer_user), client_for(owner)

    request_id = customer.post(f"{API}/me/quotation-requests", json=enquiry(vendor.id)).json()[0]["id"]
    vendor_client.post(f"{API}/me/vendor/enquiries/{request_id}/quotations", json={"quoted_amount": 45000})
    assert [n.kind for n in notes_for(db_session, customer_user)] == ["quotation.received"]
    assert "₹45,000" in notes_for(db_session, customer_user)[0].body

    quote_id = customer.get(f"{API}/me/quotations").json()[0]["id"]
    booking_id = customer.post(f"{API}/me/quotations/{quote_id}/accept").json()["id"]
    assert notes_for(db_session, owner)[-1].kind == "booking.requested"

    vendor_client.post(f"{API}/me/vendor/bookings/{booking_id}/confirm", json={})
    assert notes_for(db_session, customer_user)[-1].kind == "booking.confirmed"


def test_cancellation_notifies_the_other_party(client_for: ClientFor, db_session: Session) -> None:
    owner = make_user(db_session, role=UserRole.VENDOR)
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED, owner=owner)
    customer_user = make_user(db_session)
    booking = make_booking(db_session, customer_user, vendor, status=BookingStatus.CONFIRMED)

    client_for(customer_user).post(f"{API}/me/bookings/{booking.id}/cancel", json={"reason": "Date moved"})
    assert [n.kind for n in notes_for(db_session, owner)] == ["booking.cancelled"]
    assert notes_for(db_session, customer_user) == []  # the person who cancelled is not notified
    assert "Date moved" in notes_for(db_session, owner)[0].body


def test_admin_cancellation_notifies_both(client_for: ClientFor, db_session: Session) -> None:
    owner = make_user(db_session, role=UserRole.VENDOR)
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED, owner=owner)
    customer_user = make_user(db_session)
    booking = make_booking(db_session, customer_user, vendor)
    client_for(make_user(db_session, role=UserRole.ADMIN)).post(f"{API}/admin/bookings/{booking.id}/cancel", json={"reason": "Fraud check"})
    assert len(notes_for(db_session, owner)) == 1 and len(notes_for(db_session, customer_user)) == 1


def test_vendor_self_registration_notifies_admins_and_decision_notifies_vendor(client_for: ClientFor, db_session: Session) -> None:
    admin_user = make_user(db_session, role=UserRole.ADMIN)
    category = make_category(db_session)
    owner = make_user(db_session, role=UserRole.VENDOR)
    vendor_id = client_for(owner).post(f"{API}/me/vendor", json={
        "business_name": "Fresh Decor", "category_id": category.id, "contact_phone": "9876543210", "location": "Kamareddy",
    }).json()["id"]
    [note] = notes_for(db_session, admin_user)
    assert note.kind == "vendor.pending" and note.link == f"/admin/vendors/{vendor_id}"

    client_for(admin_user).post(f"{API}/admin/vendors/{vendor_id}/approve")
    assert [n.kind for n in notes_for(db_session, owner)] == ["vendor.approved"]


def test_admin_created_vendor_does_not_notify_admins(client_for: ClientFor, db_session: Session) -> None:
    admin_user = make_user(db_session, role=UserRole.ADMIN)
    category = make_category(db_session)
    client_for(admin_user).post(f"{API}/admin/vendors", json={
        "business_name": "Admin Added", "category_id": category.id, "contact_phone": "9876543210", "location": "Kamareddy",
    })
    assert notes_for(db_session, admin_user) == []


def test_email_opt_out_keeps_in_app(email_on, client_for: ClientFor, db_session: Session) -> None:  # type: ignore[no-untyped-def]
    owner = make_user(db_session, role=UserRole.VENDOR)
    vendor_client = client_for(owner)
    assert vendor_client.patch(f"{API}/auth/me", json={"email_notifications": False}).json()["email_notifications"] is False
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED, owner=owner)
    client_for(make_user(db_session)).post(f"{API}/me/quotation-requests", json=enquiry(vendor.id))
    assert len(notes_for(db_session, owner)) == 1
    assert emails_for(db_session, owner) == []


def test_email_disabled_marks_outbox_skipped(client_for: ClientFor, db_session: Session) -> None:
    owner = make_user(db_session, role=UserRole.VENDOR)
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED, owner=owner)
    client_for(make_user(db_session)).post(f"{API}/me/quotation-requests", json=enquiry(vendor.id))
    assert [e.status for e in emails_for(db_session, owner)] == [EmailStatus.SKIPPED]


# ---------- Notifications API ----------

def test_bell_api_list_count_and_mark_read(client_for: ClientFor, db_session: Session) -> None:
    user = make_user(db_session)
    db_session.add_all([Notification(user_id=user.id, kind="k", title=f"T{i}", body="b") for i in range(3)])
    db_session.flush()
    client = client_for(user)

    assert client.get(f"{API}/me/notifications/unread-count").json() == {"count": 3}
    items = client.get(f"{API}/me/notifications").json()["items"]
    assert [i["title"] for i in items] == ["T2", "T1", "T0"]

    assert client.post(f"{API}/me/notifications/{items[0]['id']}/read").json()["is_read"] is True
    assert client.get(f"{API}/me/notifications/unread-count").json() == {"count": 2}
    assert len(client.get(f"{API}/me/notifications", params={"unread_only": True}).json()["items"]) == 2
    assert client.post(f"{API}/me/notifications/read-all").json() == {"count": 2}
    assert client.get(f"{API}/me/notifications/unread-count").json() == {"count": 0}


def test_cannot_read_someone_elses_notifications(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session)
    note = Notification(user_id=owner.id, kind="k", title="private", body="b")
    db_session.add(note)
    db_session.flush()
    stranger = client_for(make_user(db_session))
    assert stranger.get(f"{API}/me/notifications").json()["items"] == []
    assert stranger.post(f"{API}/me/notifications/{note.id}/read").status_code == 404
    assert db_client.get(f"{API}/me/notifications/unread-count").status_code == 401


# ---------- Email delivery ----------

def _queue(db: Session, subject: str = "Hello") -> EmailOutbox:
    email = EmailOutbox(to_email="someone@example.com", subject=subject, body="Body", status=EmailStatus.PENDING)
    db.add(email)
    db.flush()
    return email


def test_outbox_sends_and_marks_sent(db_session: Session) -> None:
    email = _queue(db_session)
    sent: list[tuple[str, str, str]] = []
    assert process_outbox(db_session, lambda to, subject, body: sent.append((to, subject, body)), ids=[email.id]) == 1
    assert sent == [("someone@example.com", "Hello", "Body")]
    assert email.status == EmailStatus.SENT and email.sent_at is not None


def test_outbox_retries_then_fails(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "EMAIL_MAX_ATTEMPTS", 2)
    email = _queue(db_session)

    def broken(to: str, subject: str, body: str) -> None:
        raise ConnectionError("SMTP down")

    process_outbox(db_session, broken, ids=[email.id])
    assert email.status == EmailStatus.PENDING and email.attempts == 1 and "SMTP down" in (email.last_error or "")
    process_outbox(db_session, broken, ids=[email.id])
    assert email.status == EmailStatus.FAILED and email.attempts == 2
    process_outbox(db_session, broken, ids=[email.id])
    assert email.attempts == 2  # failed emails are not retried forever


def test_subject_line_breaks_removed(email_on, db_session: Session) -> None:  # type: ignore[no-untyped-def]
    """A business name containing line breaks must not be able to inject email headers."""
    owner = make_user(db_session, role=UserRole.VENDOR)
    notify(db_session, [owner], kind="t", title="Line1\r\nBcc: attacker@example.com", body="b")
    db_session.flush()
    [email] = emails_for(db_session, owner)
    assert "\n" not in email.subject and "\r" not in email.subject


def test_admin_test_email_endpoint(email_on, client_for: ClientFor, db_session: Session) -> None:  # type: ignore[no-untyped-def]
    admin = client_for(make_user(db_session, role=UserRole.ADMIN, email="boss@example.com"))
    delivered: list[str] = []
    app.dependency_overrides[get_email_sender] = lambda: (lambda to, subject, body: delivered.append(to))
    try:
        result = admin.post(f"{API}/admin/email/test").json()
    finally:
        app.dependency_overrides.pop(get_email_sender, None)
    assert result == {"status": "sent", "to_email": "boss@example.com", "error": None}
    assert delivered == ["boss@example.com"]
    status = admin.get(f"{API}/admin/email/status").json()
    assert status["enabled"] is True and status["counts"]["sent"] >= 1


def test_admin_test_email_when_disabled(client_for: ClientFor, db_session: Session) -> None:
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    response = admin.post(f"{API}/admin/email/test")
    assert response.status_code == 400 and "EMAIL_ENABLED" in response.json()["detail"]
    assert client_for(make_user(db_session)).get(f"{API}/admin/email/status").status_code == 403
