from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ApprovalStatus, BookingStatus, UserRole
from tests.factories import make_booking, make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]


def test_review_only_after_completed_booking(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED)
    customer_user = make_user(db_session, full_name="Ravi Kumar Reddy")
    client = client_for(customer_user)

    confirmed = make_booking(db_session, customer_user, vendor, status=BookingStatus.CONFIRMED)
    assert client.post(f"{API}/me/bookings/{confirmed.id}/review", json={"rating": 5}).status_code == 400

    completed = make_booking(db_session, customer_user, vendor, status=BookingStatus.COMPLETED)
    assert client.post(f"{API}/me/bookings/{completed.id}/review", json={"rating": 6}).status_code == 422
    created = client.post(f"{API}/me/bookings/{completed.id}/review", json={"rating": 4, "comment": "Lovely photos"})
    assert created.status_code == 201
    assert client.post(f"{API}/me/bookings/{completed.id}/review", json={"rating": 5}).status_code == 409
    assert client.get(f"{API}/me/bookings/{completed.id}").json()["has_review"] is True

    public = db_client.get(f"{API}/vendors/{vendor.slug}/reviews").json()
    assert public["average"] == 4.0 and public["count"] == 1
    assert public["items"][0]["reviewer_name"] == "Ravi R."  # no full name exposed
    assert "customer" not in public["items"][0]
    detail = db_client.get(f"{API}/vendors/{vendor.slug}").json()
    assert detail["rating_average"] == 4.0 and detail["review_count"] == 1


def test_cannot_review_someone_elses_booking(client_for: ClientFor, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED)
    booking = make_booking(db_session, make_user(db_session), vendor, status=BookingStatus.COMPLETED)
    stranger = client_for(make_user(db_session))
    assert stranger.post(f"{API}/me/bookings/{booking.id}/review", json={"rating": 1}).status_code == 404


def test_no_reviews_means_no_rating(db_client: TestClient, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED)
    detail = db_client.get(f"{API}/vendors/{vendor.slug}").json()
    assert detail["rating_average"] is None and detail["review_count"] == 0


def test_hidden_review_excluded_and_rating_sort(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session, "Decor")
    good = make_vendor(db_session, category, "Good Decor", status=ApprovalStatus.APPROVED)
    okay = make_vendor(db_session, category, "Okay Decor", status=ApprovalStatus.APPROVED)
    unrated = make_vendor(db_session, category, "New Decor", status=ApprovalStatus.APPROVED)
    customer_user = make_user(db_session)
    client = client_for(customer_user)
    for vendor, rating in ((good, 5), (okay, 3)):
        booking = make_booking(db_session, customer_user, vendor, status=BookingStatus.COMPLETED)
        client.post(f"{API}/me/bookings/{booking.id}/review", json={"rating": rating})

    order = [v["slug"] for v in db_client.get(f"{API}/vendors", params={"category": "decor", "sort": "rating"}).json()["items"]]
    assert order == [good.slug, okay.slug, unrated.slug]
    assert [v["slug"] for v in db_client.get(f"{API}/vendors", params={"min_rating": 4}).json()["items"]] == [good.slug]

    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    review_id = admin.get(f"{API}/admin/reviews", params={"vendor_id": good.id}).json()["items"][0]["id"]
    assert admin.patch(f"{API}/admin/reviews/{review_id}", json={"is_visible": False}).json()["is_visible"] is False
    assert db_client.get(f"{API}/vendors/{good.slug}").json()["review_count"] == 0


def test_report_listing_and_admin_resolution(client_for: ClientFor, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED)
    reporter = client_for(make_user(db_session))
    created = reporter.post(f"{API}/reports", json={"vendor_id": vendor.id, "reason": "wrong_information", "details": "Wrong phone"})
    assert created.status_code == 201 and created.json()["status"] == "open"
    assert reporter.post(f"{API}/reports", json={"vendor_id": vendor.id, "reason": "other"}).status_code == 409
    assert reporter.post(f"{API}/reports", json={"reason": "other"}).status_code == 422

    assert reporter.get(f"{API}/admin/reports").status_code == 403
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    open_reports = admin.get(f"{API}/admin/reports", params={"status": "open"}).json()
    assert open_reports["total"] == 1 and open_reports["items"][0]["vendor"]["id"] == vendor.id

    report_id = created.json()["id"]
    resolved = admin.post(f"{API}/admin/reports/{report_id}/resolve", json={"status": "resolved", "admin_notes": "Phone fixed"})
    assert resolved.json()["status"] == "resolved"
    assert admin.post(f"{API}/admin/reports/{report_id}/resolve", json={"status": "dismissed"}).status_code == 400


def test_anonymous_cannot_report(db_client: TestClient, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED)
    assert db_client.post(f"{API}/reports", json={"vendor_id": vendor.id, "reason": "other"}).status_code == 401
