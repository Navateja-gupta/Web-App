from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.enums import ApprovalStatus, BookingStatus, PricingType, UserRole
from app.models.package import VendorPackage
from app.models.wedding_plan import WeddingPlan, WeddingPlanItem
from tests.factories import make_booking, make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]


def vendor_and_owner(db: Session):  # type: ignore[no-untyped-def]
    owner = make_user(db, role=UserRole.VENDOR)
    return make_vendor(db, make_category(db), status=ApprovalStatus.APPROVED, owner=owner), owner


def test_direct_booking_request_and_vendor_confirmation(client_for: ClientFor, db_session: Session) -> None:
    vendor, owner = vendor_and_owner(db_session)
    package = VendorPackage(vendor_id=vendor.id, name="Gold", pricing_type=PricingType.FIXED, price=Decimal("75000"))
    db_session.add(package)
    db_session.flush()
    customer = client_for(make_user(db_session))
    event = (date.today() + timedelta(days=45)).isoformat()

    created = customer.post(f"{API}/me/bookings", json={"vendor_id": vendor.id, "package_id": package.id, "event_date": event})
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["booking_status"] == "requested" and booking["package"]["name"] == "Gold"
    assert customer.post(f"{API}/me/bookings", json={"vendor_id": vendor.id, "event_date": event}).status_code == 409

    vendor_client = client_for(owner)
    assert vendor_client.post(f"{API}/me/vendor/bookings/{booking['id']}/confirm", json={}).status_code == 400  # no amount
    confirmed = vendor_client.post(f"{API}/me/vendor/bookings/{booking['id']}/confirm", json={"agreed_amount": 72000})
    assert confirmed.status_code == 200
    assert confirmed.json()["booking_status"] == "confirmed" and confirmed.json()["agreed_amount"] == 72000.0
    assert db_session.scalar(select(AuditLog).where(AuditLog.action == "booking.confirmed"))


def test_customer_cannot_confirm_or_complete(client_for: ClientFor, db_session: Session) -> None:
    vendor, _ = vendor_and_owner(db_session)
    customer_user = make_user(db_session)
    booking = make_booking(db_session, customer_user, vendor)
    customer = client_for(customer_user)
    assert customer.post(f"{API}/me/vendor/bookings/{booking.id}/confirm", json={}).status_code == 403


def test_invalid_transitions(client_for: ClientFor, db_session: Session) -> None:
    vendor, owner = vendor_and_owner(db_session)
    customer_user = make_user(db_session)
    vendor_client = client_for(owner)

    requested = make_booking(db_session, customer_user, vendor)
    assert vendor_client.post(f"{API}/me/vendor/bookings/{requested.id}/complete").status_code == 400

    cancelled = make_booking(db_session, customer_user, vendor, status=BookingStatus.CANCELLED)
    assert vendor_client.post(f"{API}/me/vendor/bookings/{cancelled.id}/confirm", json={}).status_code == 400

    future_confirmed = make_booking(db_session, customer_user, vendor, status=BookingStatus.CONFIRMED)
    assert vendor_client.post(f"{API}/me/vendor/bookings/{future_confirmed.id}/complete").status_code == 400  # before event

    past_confirmed = make_booking(db_session, customer_user, vendor, status=BookingStatus.CONFIRMED,
                                  event_date=date.today() - timedelta(days=1))
    done = vendor_client.post(f"{API}/me/vendor/bookings/{past_confirmed.id}/complete")
    assert done.status_code == 200 and done.json()["booking_status"] == "completed"
    assert vendor_client.post(f"{API}/me/vendor/bookings/{past_confirmed.id}/cancel", json={"reason": "x"}).status_code == 400


def test_reject_and_cancel_require_reason(client_for: ClientFor, db_session: Session) -> None:
    vendor, owner = vendor_and_owner(db_session)
    customer_user = make_user(db_session)
    booking = make_booking(db_session, customer_user, vendor)
    vendor_client = client_for(owner)
    assert vendor_client.post(f"{API}/me/vendor/bookings/{booking.id}/reject", json={}).status_code == 400
    rejected = vendor_client.post(f"{API}/me/vendor/bookings/{booking.id}/reject", json={"reason": "Date not available"}).json()
    assert rejected["booking_status"] == "rejected" and rejected["cancellation_reason"] == "Date not available"

    other = make_booking(db_session, customer_user, vendor, status=BookingStatus.CONFIRMED)
    customer = client_for(customer_user)
    cancelled = customer.post(f"{API}/me/bookings/{other.id}/cancel", json={"reason": "Wedding postponed"})
    assert cancelled.json()["booking_status"] == "cancelled"


def test_bookings_are_private(client_for: ClientFor, db_session: Session) -> None:
    vendor, _ = vendor_and_owner(db_session)
    other_vendor, other_owner = vendor_and_owner(db_session)
    booking = make_booking(db_session, make_user(db_session), vendor)

    stranger = client_for(make_user(db_session))
    assert stranger.get(f"{API}/me/bookings/{booking.id}").status_code == 404
    assert stranger.post(f"{API}/me/bookings/{booking.id}/cancel", json={"reason": "x"}).status_code == 404
    assert client_for(other_owner).post(f"{API}/me/vendor/bookings/{booking.id}/confirm", json={"agreed_amount": 1}).status_code == 404
    assert other_vendor.id != vendor.id


def test_admin_can_list_and_cancel(client_for: ClientFor, db_session: Session) -> None:
    vendor, _ = vendor_and_owner(db_session)
    booking = make_booking(db_session, make_user(db_session), vendor, status=BookingStatus.CONFIRMED)
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    listed = admin.get(f"{API}/admin/bookings", params={"status": "confirmed"}).json()
    assert [b["id"] for b in listed["items"]] == [booking.id]
    assert admin.post(f"{API}/admin/bookings/{booking.id}/cancel", json={"reason": "Vendor complaint"}).json()["booking_status"] == "cancelled"


def test_confirmed_booking_is_added_to_wedding_plan(client_for: ClientFor, db_session: Session) -> None:
    vendor, owner = vendor_and_owner(db_session)
    customer_user = make_user(db_session)
    plan = WeddingPlan(customer_id=customer_user.id, event_name="Wedding", estimated_budget=Decimal("500000"))
    db_session.add(plan)
    db_session.flush()
    booking = make_booking(db_session, customer_user, vendor, agreed_amount=Decimal("80000"))
    booking.wedding_plan_id = plan.id
    db_session.flush()

    client_for(owner).post(f"{API}/me/vendor/bookings/{booking.id}/confirm", json={})
    item = db_session.scalar(select(WeddingPlanItem).where(WeddingPlanItem.wedding_plan_id == plan.id))
    assert item is not None and item.estimated_cost == Decimal("80000") and item.vendor_id == vendor.id
