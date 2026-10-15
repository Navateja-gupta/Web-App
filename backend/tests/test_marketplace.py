"""Phase 4: customer-facing search and shortlists."""

from collections.abc import Callable
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ApprovalStatus, AvailabilityStatus, PricingType, UserRole
from app.models.package import VendorPackage
from app.models.vendor import VendorAvailability
from tests.factories import make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]


def slugs(client: TestClient, **params: object) -> list[str]:
    response = client.get(f"{API}/vendors", params=params)
    assert response.status_code == 200, response.text
    return [v["slug"] for v in response.json()["items"]]


# ---------- Search ----------

def test_search_matches_package_names_and_category(db_client: TestClient, db_session: Session) -> None:
    photo = make_category(db_session, "Photography")
    vendor = make_vendor(db_session, photo, "Sri Studio", status=ApprovalStatus.APPROVED)
    db_session.add(VendorPackage(vendor_id=vendor.id, name="Drone coverage", pricing_type=PricingType.FIXED, price=5000))
    db_session.add(VendorPackage(vendor_id=vendor.id, name="Hidden album", pricing_type=PricingType.FIXED, price=1, is_active=False))
    db_session.flush()

    assert slugs(db_client, q="drone") == [vendor.slug]
    assert slugs(db_client, q="photograph") == [vendor.slug]
    assert slugs(db_client, q="hidden album") == []  # inactive packages are not searchable


def test_available_on_uses_only_declared_availability(db_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session)
    day = date.today() + timedelta(days=30)
    free = make_vendor(db_session, category, status=ApprovalStatus.APPROVED)
    booked = make_vendor(db_session, category, status=ApprovalStatus.APPROVED)
    make_vendor(db_session, category, status=ApprovalStatus.APPROVED)  # no data: unknown, not free
    db_session.add_all([
        VendorAvailability(vendor_id=free.id, date=day, availability_status=AvailabilityStatus.AVAILABLE),
        VendorAvailability(vendor_id=booked.id, date=day, availability_status=AvailabilityStatus.BOOKED),
    ])
    db_session.flush()
    assert slugs(db_client, available_on=day.isoformat()) == [free.slug]


def test_min_price_above_max_price_rejected(db_client: TestClient) -> None:
    response = db_client.get(f"{API}/vendors", params={"min_price": 5000, "max_price": 1000})
    assert response.status_code == 400


def test_pagination_metadata(db_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session, "Catering")
    for _ in range(5):
        make_vendor(db_session, category, status=ApprovalStatus.APPROVED)
    body = db_client.get(f"{API}/vendors", params={"category": "catering", "size": 2, "page": 3}).json()
    assert body["total"] == 5 and body["pages"] == 3 and len(body["items"]) == 1


def test_locations_list_only_public_vendors(db_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session)
    make_vendor(db_session, category, status=ApprovalStatus.APPROVED, location="Kamareddy",
                service_areas=["Yellareddy", "kamareddy"])
    make_vendor(db_session, category, status=ApprovalStatus.PENDING, location="Secret Town")
    assert db_client.get(f"{API}/vendors/locations").json() == ["Kamareddy", "Yellareddy"]


# ---------- Shortlist ----------

def test_customer_shortlist_flow(client_for: ClientFor, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED)
    client = client_for(make_user(db_session, role=UserRole.CUSTOMER))

    first = client.put(f"{API}/me/shortlist/{vendor.id}")
    assert first.status_code == 200 and first.json()["vendor"]["id"] == vendor.id
    assert client.put(f"{API}/me/shortlist/{vendor.id}").status_code == 200  # idempotent

    items = client.get(f"{API}/me/shortlist").json()
    assert [i["vendor"]["slug"] for i in items] == [vendor.slug]
    assert client.get(f"{API}/me/shortlist/ids").json() == [vendor.id]

    assert client.delete(f"{API}/me/shortlist/{vendor.id}").status_code == 204
    assert client.get(f"{API}/me/shortlist").json() == []
    assert client.delete(f"{API}/me/shortlist/{vendor.id}").status_code == 204  # idempotent


def test_cannot_shortlist_unlisted_vendor(client_for: ClientFor, db_session: Session) -> None:
    pending = make_vendor(db_session, make_category(db_session))
    client = client_for(make_user(db_session, role=UserRole.CUSTOMER))
    assert client.put(f"{API}/me/shortlist/{pending.id}").status_code == 404
    assert client.put(f"{API}/me/shortlist/999999").status_code == 404


def test_suspended_vendor_drops_out_of_shortlist(client_for: ClientFor, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED)
    client = client_for(make_user(db_session, role=UserRole.CUSTOMER))
    client.put(f"{API}/me/shortlist/{vendor.id}")
    vendor.approval_status = ApprovalStatus.SUSPENDED
    db_session.flush()
    assert client.get(f"{API}/me/shortlist").json() == []


def test_shortlists_are_private_per_customer(client_for: ClientFor, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED)
    alice = client_for(make_user(db_session, role=UserRole.CUSTOMER))
    bob = client_for(make_user(db_session, role=UserRole.CUSTOMER))
    alice.put(f"{API}/me/shortlist/{vendor.id}")
    assert bob.get(f"{API}/me/shortlist").json() == []


def test_only_customers_have_shortlists(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    assert db_client.get(f"{API}/me/shortlist").status_code == 401
    for role in (UserRole.VENDOR, UserRole.ADMIN):
        assert client_for(make_user(db_session, role=role)).get(f"{API}/me/shortlist").status_code == 403
