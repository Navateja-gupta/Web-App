from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ApprovalStatus, UserRole
from app.models.user import User
from app.models.vendor import Vendor
from tests.factories import make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]


def vendor_with_owner(db: Session, status: ApprovalStatus = ApprovalStatus.APPROVED) -> tuple[Vendor, User]:
    owner = make_user(db, role=UserRole.VENDOR)
    return make_vendor(db, make_category(db), status=status, owner=owner), owner


def test_package_pricing_rules(client_for: ClientFor, db_session: Session) -> None:
    _, owner = vendor_with_owner(db_session)
    client = client_for(owner)
    url = f"{API}/me/vendor/packages"

    assert client.post(url, json={"name": "Basic", "pricing_type": "fixed"}).status_code == 400
    assert client.post(url, json={"name": "Range", "pricing_type": "starting_from", "price": 50000, "price_max": 40000}).status_code == 400

    quote = client.post(url, json={"name": "Custom", "pricing_type": "quote_on_request", "price": 999})
    assert quote.status_code == 201 and quote.json()["price"] is None

    per_plate = client.post(url, json={
        "name": "Veg Meals", "pricing_type": "per_person", "price": "350.50",
        "inclusions": ["Rice", "Dal", " rice "], "exclusions": ["Service staff tips"],
    })
    assert per_plate.status_code == 201
    assert per_plate.json()["price"] == 350.5
    assert per_plate.json()["inclusions"] == ["Rice", "Dal"]

    assert client.post(url, json={"name": "veg meals", "pricing_type": "fixed", "price": 1}).status_code == 409


def test_update_deactivate_and_public_visibility(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    vendor, owner = vendor_with_owner(db_session)
    client = client_for(owner)
    package_id = client.post(
        f"{API}/me/vendor/packages", json={"name": "Gold", "pricing_type": "fixed", "price": 60000}
    ).json()["id"]

    updated = client.patch(f"{API}/me/vendor/packages/{package_id}", json={"price": 65000})
    assert updated.json()["price"] == 65000.0
    assert [p["name"] for p in db_client.get(f"{API}/vendors/{vendor.slug}/packages").json()] == ["Gold"]

    client.patch(f"{API}/me/vendor/packages/{package_id}", json={"is_active": False})
    assert db_client.get(f"{API}/vendors/{vendor.slug}/packages").json() == []
    assert len(client.get(f"{API}/me/vendor/packages").json()) == 1  # owner still sees it

    assert client.delete(f"{API}/me/vendor/packages/{package_id}").status_code == 204
    assert client.get(f"{API}/me/vendor/packages").json() == []


def test_packages_of_unapproved_vendor_are_not_public(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    vendor, owner = vendor_with_owner(db_session, status=ApprovalStatus.PENDING)
    client_for(owner).post(f"{API}/me/vendor/packages", json={"name": "Silver", "pricing_type": "fixed", "price": 1000})
    assert db_client.get(f"{API}/vendors/{vendor.slug}/packages").status_code == 404


def test_vendor_cannot_touch_another_vendors_package(client_for: ClientFor, db_session: Session) -> None:
    _, owner_a = vendor_with_owner(db_session)
    _, owner_b = vendor_with_owner(db_session)
    package_id = client_for(owner_a).post(
        f"{API}/me/vendor/packages", json={"name": "A only", "pricing_type": "fixed", "price": 100}
    ).json()["id"]

    intruder = client_for(owner_b)
    assert intruder.patch(f"{API}/me/vendor/packages/{package_id}", json={"price": 1}).status_code == 404
    assert intruder.delete(f"{API}/me/vendor/packages/{package_id}").status_code == 404
    assert intruder.get(f"{API}/admin/vendors/1/packages").status_code == 403


def test_admin_manages_packages_for_admin_created_vendor(client_for: ClientFor, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session))
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    created = admin.post(
        f"{API}/admin/vendors/{vendor.id}/packages", json={"name": "Standard", "pricing_type": "fixed", "price": 40000}
    )
    assert created.status_code == 201
    assert created.json()["vendor_id"] == vendor.id
    assert len(admin.get(f"{API}/admin/vendors/{vendor.id}/packages").json()) == 1
