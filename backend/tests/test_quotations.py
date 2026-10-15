from collections.abc import Callable
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.enums import ApprovalStatus, UserRole
from app.models.quotation import Quotation
from app.models.vendor import Vendor
from tests.factories import make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]
FUTURE = (date.today() + timedelta(days=60)).isoformat()


@pytest.fixture
def setup(client_for: ClientFor, db_session: Session):  # type: ignore[no-untyped-def]
    category = make_category(db_session, "Photography")
    owner_a = make_user(db_session, role=UserRole.VENDOR)
    owner_b = make_user(db_session, role=UserRole.VENDOR)
    vendor_a = make_vendor(db_session, category, "Studio A", status=ApprovalStatus.APPROVED, owner=owner_a)
    vendor_b = make_vendor(db_session, category, "Studio B", status=ApprovalStatus.APPROVED, owner=owner_b)
    customer = make_user(db_session, role=UserRole.CUSTOMER, full_name="Priya Sharma")
    return {
        "vendor_a": vendor_a, "vendor_b": vendor_b, "customer_user": customer,
        "customer": client_for(customer), "a": client_for(owner_a), "b": client_for(owner_b),
    }


def enquiry(vendor_ids: list[int], **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "vendor_ids": vendor_ids, "service_date": FUTURE, "event_location": "Function hall, Kamareddy",
        "guest_count": 300, "requirements": "Candid photos and a traditional album for a two-day wedding.",
        "budget": 60000,
    }
    body.update(overrides)
    return body


def send_quote(client: TestClient, request_id: int, amount: int, **extra: object) -> dict:  # type: ignore[type-arg]
    response = client.post(f"{API}/me/vendor/enquiries/{request_id}/quotations", json={"quoted_amount": amount, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_full_enquiry_to_booking_request_flow(setup, db_session: Session) -> None:  # type: ignore[no-untyped-def]
    a, b, customer = setup["a"], setup["b"], setup["customer"]
    vendor_a: Vendor = setup["vendor_a"]
    vendor_b: Vendor = setup["vendor_b"]

    created = customer.post(f"{API}/me/quotation-requests", json=enquiry([vendor_a.id, vendor_b.id]))
    assert created.status_code == 201, created.text
    requests = {r["vendor"]["id"]: r for r in created.json()}
    assert {r["status"] for r in requests.values()} == {"pending"}

    # Each vendor only sees their own enquiry, with the customer's contact details.
    inbox_a = a.get(f"{API}/me/vendor/enquiries").json()
    assert inbox_a["total"] == 1 and inbox_a["items"][0]["customer"]["full_name"] == "Priya Sharma"

    send_quote(a, requests[vendor_a.id]["id"], 55000, inclusions=["Album", "Drone"])
    send_quote(b, requests[vendor_b.id]["id"], 48000)

    quotes = customer.get(f"{API}/me/quotations").json()
    assert sorted(q["quoted_amount"] for q in quotes) == [48000.0, 55000.0]
    quote_b = next(q for q in quotes if q["vendor"]["id"] == vendor_b.id)

    accepted = customer.post(f"{API}/me/quotations/{quote_b['id']}/accept")
    assert accepted.status_code == 201, accepted.text
    booking = accepted.json()
    assert booking["booking_status"] == "requested"  # vendor must still confirm
    assert booking["agreed_amount"] == 48000.0
    assert booking["quotation_id"] == quote_b["id"]

    req_b = customer.get(f"{API}/me/quotation-requests/{requests[vendor_b.id]['id']}").json()
    assert req_b["status"] == "closed"
    # The other vendor's enquiry is separate and still open.
    assert customer.get(f"{API}/me/quotation-requests/{requests[vendor_a.id]['id']}").json()["status"] == "quoted"

    assert customer.post(f"{API}/me/quotations/{quote_b['id']}/accept").status_code == 400  # not twice
    assert db_session.scalar(select(AuditLog).where(AuditLog.action == "quotation.accepted"))


def test_revised_quotation_replaces_previous(setup) -> None:  # type: ignore[no-untyped-def]
    customer, a = setup["customer"], setup["a"]
    request_id = customer.post(f"{API}/me/quotation-requests", json=enquiry([setup["vendor_a"].id])).json()[0]["id"]
    first = send_quote(a, request_id, 70000)
    second = send_quote(a, request_id, 65000)
    statuses = {q["quoted_amount"]: q["status"] for q in second["quotations"]}
    assert statuses == {70000.0: "withdrawn", 65000.0: "sent"}
    assert first["quotations"][0]["status"] == "sent"


def test_expired_quotation_cannot_be_accepted(setup, db_session: Session) -> None:  # type: ignore[no-untyped-def]
    customer, a = setup["customer"], setup["a"]
    request_id = customer.post(f"{API}/me/quotation-requests", json=enquiry([setup["vendor_a"].id])).json()[0]["id"]
    quote_id = send_quote(a, request_id, 40000, validity_date=date.today().isoformat())["quotations"][0]["id"]
    db_session.execute(
        Quotation.__table__.update().where(Quotation.id == quote_id).values(validity_date=date.today() - timedelta(days=1))
    )
    assert customer.post(f"{API}/me/quotations/{quote_id}/accept").status_code == 400
    assert customer.get(f"{API}/me/quotations").json()[0]["status"] == "expired"


def test_enquiry_validation(setup, db_session: Session) -> None:  # type: ignore[no-untyped-def]
    customer = setup["customer"]
    vendor_id = setup["vendor_a"].id
    past = (date.today() - timedelta(days=1)).isoformat()
    assert customer.post(f"{API}/me/quotation-requests", json=enquiry([vendor_id], service_date=past)).status_code == 400
    assert customer.post(f"{API}/me/quotation-requests", json=enquiry([vendor_id], requirements="short")).status_code == 422
    pending_vendor = make_vendor(db_session, make_category(db_session))
    assert customer.post(f"{API}/me/quotation-requests", json=enquiry([pending_vendor.id])).status_code == 404

    assert customer.post(f"{API}/me/quotation-requests", json=enquiry([vendor_id])).status_code == 201
    assert customer.post(f"{API}/me/quotation-requests", json=enquiry([vendor_id])).status_code == 409


def test_all_or_nothing_when_one_vendor_is_invalid(setup, db_session: Session) -> None:  # type: ignore[no-untyped-def]
    customer = setup["customer"]
    hidden = make_vendor(db_session, make_category(db_session))
    response = customer.post(f"{API}/me/quotation-requests", json=enquiry([setup["vendor_a"].id, hidden.id]))
    assert response.status_code == 404
    assert customer.get(f"{API}/me/quotation-requests").json() == []


def test_privacy_between_customers_and_vendors(setup, client_for: ClientFor, db_session: Session) -> None:  # type: ignore[no-untyped-def]
    customer, a, b = setup["customer"], setup["a"], setup["b"]
    request_id = customer.post(f"{API}/me/quotation-requests", json=enquiry([setup["vendor_a"].id])).json()[0]["id"]
    quote_id = send_quote(a, request_id, 30000)["quotations"][0]["id"]

    other_customer = client_for(make_user(db_session, role=UserRole.CUSTOMER))
    assert other_customer.get(f"{API}/me/quotation-requests/{request_id}").status_code == 404
    assert other_customer.post(f"{API}/me/quotations/{quote_id}/accept").status_code == 404
    assert other_customer.get(f"{API}/me/quotations").json() == []

    assert b.get(f"{API}/me/vendor/enquiries/{request_id}").status_code == 404
    assert b.post(f"{API}/me/vendor/enquiries/{request_id}/quotations", json={"quoted_amount": 1}).status_code == 404
    assert b.post(f"{API}/me/vendor/quotations/{quote_id}/withdraw").status_code == 404

    # Vendors cannot use customer endpoints and vice versa.
    assert a.post(f"{API}/me/quotation-requests", json=enquiry([setup["vendor_b"].id])).status_code == 403
    assert customer.get(f"{API}/me/vendor/enquiries").status_code == 403


def test_decline_and_cancel(setup) -> None:  # type: ignore[no-untyped-def]
    customer, a = setup["customer"], setup["a"]
    ids = [r["id"] for r in customer.post(
        f"{API}/me/quotation-requests", json=enquiry([setup["vendor_a"].id, setup["vendor_b"].id])
    ).json()]
    req_a = next(i for i in ids if a.get(f"{API}/me/vendor/enquiries/{i}").status_code == 200)
    req_b = next(i for i in ids if i != req_a)

    declined = a.post(f"{API}/me/vendor/enquiries/{req_a}/decline", json={"reason": "Fully booked that week"}).json()
    assert declined["status"] == "declined"
    assert customer.get(f"{API}/me/quotation-requests/{req_a}").json()["vendor_response"] == "Fully booked that week"
    assert a.post(f"{API}/me/vendor/enquiries/{req_a}/quotations", json={"quoted_amount": 1}).status_code == 400

    assert customer.post(f"{API}/me/quotation-requests/{req_b}/cancel").json()["status"] == "cancelled"
    assert customer.post(f"{API}/me/quotation-requests/{req_b}/cancel").status_code == 400


def test_withdraw_quotation(setup) -> None:  # type: ignore[no-untyped-def]
    customer, a = setup["customer"], setup["a"]
    request_id = customer.post(f"{API}/me/quotation-requests", json=enquiry([setup["vendor_a"].id])).json()[0]["id"]
    quote_id = send_quote(a, request_id, 30000)["quotations"][0]["id"]
    body = a.post(f"{API}/me/vendor/quotations/{quote_id}/withdraw").json()
    assert body["status"] == "pending" and body["quotations"][0]["status"] == "withdrawn"
    assert customer.post(f"{API}/me/quotations/{quote_id}/accept").status_code == 400

