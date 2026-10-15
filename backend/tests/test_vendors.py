from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.enums import ApprovalStatus, UserRole
from app.models.vendor import Vendor
from tests.factories import make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]


def vendor_payload(category_id: int, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "business_name": "Sample Photo Studio",
        "category_id": category_id,
        "description": "Candid and traditional wedding photography.",
        "contact_phone": "9876543210",
        "contact_email": "Studio@Example.com",
        "location": "Kamareddy",
        "service_areas": ["Kamareddy", "Nizamabad", " kamareddy ", ""],
        "starting_price": "25000",
    }
    payload.update(overrides)
    return payload


def public_slugs(client: TestClient, **params: object) -> list[str]:
    return [v["slug"] for v in client.get(f"{API}/vendors", params=params).json()["items"]]


# ---------- Vendor self-registration ----------

def test_vendor_self_registration_starts_pending_and_hidden(
    client_for: ClientFor, db_client: TestClient, db_session: Session
) -> None:
    category = make_category(db_session, "Photography")
    vendor_client = client_for(make_user(db_session, role=UserRole.VENDOR))

    response = vendor_client.post(f"{API}/me/vendor", json=vendor_payload(category.id))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["approval_status"] == "pending"
    assert body["contact_phone"] == "+919876543210"
    assert body["contact_email"] == "studio@example.com"
    assert body["service_areas"] == ["Kamareddy", "Nizamabad"]
    assert body["starting_price"] == 25000.0

    assert public_slugs(db_client, category="photography") == []
    assert db_client.get(f"{API}/vendors/{body['slug']}").status_code == 404
    assert vendor_client.get(f"{API}/me/vendor").json()["id"] == body["id"]


def test_vendor_cannot_create_second_profile(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session)
    client = client_for(make_user(db_session, role=UserRole.VENDOR))
    assert client.post(f"{API}/me/vendor", json=vendor_payload(category.id)).status_code == 201
    assert client.post(f"{API}/me/vendor", json=vendor_payload(category.id, business_name="Other")).status_code == 409


def test_customer_cannot_create_vendor_profile(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session)
    client = client_for(make_user(db_session, role=UserRole.CUSTOMER))
    assert client.post(f"{API}/me/vendor", json=vendor_payload(category.id)).status_code == 403


def test_inactive_category_cannot_be_chosen(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session, is_active=False)
    client = client_for(make_user(db_session, role=UserRole.VENDOR))
    assert client.post(f"{API}/me/vendor", json=vendor_payload(category.id)).status_code == 400


def test_duplicate_business_name_in_category_rejected(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session)
    make_vendor(db_session, category, "Sample Photo Studio")
    client = client_for(make_user(db_session, role=UserRole.VENDOR))
    assert client.post(f"{API}/me/vendor", json=vendor_payload(category.id)).status_code == 409


def test_vendor_cannot_approve_self_or_change_status(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session)
    client = client_for(make_user(db_session, role=UserRole.VENDOR))
    vendor_id = client.post(f"{API}/me/vendor", json=vendor_payload(category.id)).json()["id"]

    assert client.post(f"{API}/admin/vendors/{vendor_id}/approve").status_code == 403
    response = client.patch(f"{API}/me/vendor", json={"approval_status": "approved", "is_active": False, "is_verified": True})
    assert response.status_code == 200
    assert response.json()["approval_status"] == "pending"
    assert response.json()["is_active"] is True
    assert response.json()["is_verified"] is False


# ---------- Admin-created vendors and approval ----------

def test_admin_creates_vendor_then_approves_and_it_appears(
    client_for: ClientFor, db_client: TestClient, db_session: Session
) -> None:
    category = make_category(db_session, "Photography")
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))

    created = admin.post(f"{API}/admin/vendors", json=vendor_payload(category.id))
    assert created.status_code == 201, created.text
    vendor = created.json()
    assert vendor["approval_status"] == "pending"
    assert vendor["user"] is None
    assert public_slugs(db_client, category="photography") == []

    approved = admin.post(f"{API}/admin/vendors/{vendor['id']}/approve")
    assert approved.status_code == 200 and approved.json()["approval_status"] == "approved"

    assert public_slugs(db_client, category="photography") == [vendor["slug"]]
    assert db_client.get(f"{API}/categories/photography").json()["vendor_count"] == 1
    detail = db_client.get(f"{API}/vendors/{vendor['slug']}").json()
    for internal in ("approval_status", "status_reason", "verification_notes", "user", "created_by_id"):
        assert internal not in detail

    assert db_session.scalar(select(AuditLog).where(AuditLog.action == "vendor.approved", AuditLog.entity_id == vendor["id"]))


def test_dynamic_onboarding_three_then_four_more_photographers(
    client_for: ClientFor, db_client: TestClient, db_session: Session
) -> None:
    """The exact scenario from the requirements: counts come from the database."""
    category = make_category(db_session, "Photography")
    for _ in range(3):
        make_vendor(db_session, category, status=ApprovalStatus.APPROVED)
    assert db_client.get(f"{API}/categories/photography").json()["vendor_count"] == 3

    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    for i in range(4):
        vendor_id = admin.post(
            f"{API}/admin/vendors", json=vendor_payload(category.id, business_name=f"New Photographer {i}")
        ).json()["id"]
        assert admin.post(f"{API}/admin/vendors/{vendor_id}/approve").status_code == 200

    assert db_client.get(f"{API}/categories/photography").json()["vendor_count"] == 7
    assert db_client.get(f"{API}/vendors", params={"category": "photography"}).json()["total"] == 7


def test_reject_requires_reason_and_vendor_edit_resubmits(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session)
    vendor_user = make_user(db_session, role=UserRole.VENDOR)
    vendor = make_vendor(db_session, category, owner=vendor_user)
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))

    assert admin.post(f"{API}/admin/vendors/{vendor.id}/reject").status_code == 400
    rejected = admin.post(f"{API}/admin/vendors/{vendor.id}/reject", json={"reason": "Please add real photos"})
    assert rejected.json()["approval_status"] == "rejected"

    owner = client_for(vendor_user)
    mine = owner.get(f"{API}/me/vendor").json()
    assert mine["status_reason"] == "Please add real photos"

    resubmitted = owner.patch(f"{API}/me/vendor", json={"description": "Updated with portfolio"}).json()
    assert resubmitted["approval_status"] == "pending"
    assert resubmitted["status_reason"] is None


def test_suspend_and_reinstate(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session, "Decor"), status=ApprovalStatus.APPROVED)
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    assert public_slugs(db_client, category="decor") == [vendor.slug]

    assert admin.post(f"{API}/admin/vendors/{vendor.id}/suspend", json={"reason": "Customer complaint"}).status_code == 200
    assert public_slugs(db_client, category="decor") == []

    assert admin.post(f"{API}/admin/vendors/{vendor.id}/approve").status_code == 200
    assert public_slugs(db_client, category="decor") == [vendor.slug]


def test_invalid_transitions_rejected(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session)
    approved = make_vendor(db_session, category, status=ApprovalStatus.APPROVED)
    pending = make_vendor(db_session, category)
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    assert admin.post(f"{API}/admin/vendors/{approved.id}/reject", json={"reason": "x" * 10}).status_code == 400
    assert admin.post(f"{API}/admin/vendors/{pending.id}/suspend", json={"reason": "x" * 10}).status_code == 400
    assert admin.post(f"{API}/admin/vendors/{approved.id}/approve").status_code == 400


def test_admin_deactivation_hides_vendor_but_keeps_approval(
    client_for: ClientFor, db_client: TestClient, db_session: Session
) -> None:
    vendor = make_vendor(db_session, make_category(db_session, "Catering"), status=ApprovalStatus.APPROVED)
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    body = admin.patch(f"{API}/admin/vendors/{vendor.id}", json={"is_active": False}).json()
    assert body["is_active"] is False and body["approval_status"] == "approved"
    assert public_slugs(db_client, category="catering") == []


def test_category_change_by_approved_vendor_needs_review(client_for: ClientFor, db_session: Session) -> None:
    vendor_user = make_user(db_session, role=UserRole.VENDOR)
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED, owner=vendor_user)
    other = make_category(db_session)
    body = client_for(vendor_user).patch(f"{API}/me/vendor", json={"category_id": other.id}).json()
    assert body["approval_status"] == "pending"
    db_session.refresh(vendor)
    assert vendor.category_id == other.id


def test_vendor_routes_require_profile(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session, role=UserRole.VENDOR))
    assert client.get(f"{API}/me/vendor").status_code == 404
    assert client.get(f"{API}/me/vendor/packages").status_code == 404


def test_admin_list_filters_and_counts(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session)
    make_vendor(db_session, category, "Pending One")
    make_vendor(db_session, category, "Approved One", status=ApprovalStatus.APPROVED)
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    pending = admin.get(f"{API}/admin/vendors", params={"approval_status": "pending"}).json()
    assert [v["business_name"] for v in pending["items"]] == ["Pending One"]
    counts = admin.get(f"{API}/admin/vendors/status-counts").json()
    assert counts["pending"] == 1 and counts["approved"] == 1 and counts["rejected"] == 0


def test_verification_is_explicit(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED)
    assert db_client.get(f"{API}/vendors/{vendor.slug}").json()["is_verified"] is False
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    body = admin.post(
        f"{API}/admin/vendors/{vendor.id}/verification", json={"is_verified": True, "notes": "Met in person, saw GST"}
    ).json()
    assert body["is_verified"] is True and body["verification_notes"] == "Met in person, saw GST"
    public = db_client.get(f"{API}/vendors/{vendor.slug}").json()
    assert public["is_verified"] is True and "verification_notes" not in public


# ---------- Public search ----------

def test_public_search_filters_and_sorting(db_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session, "Photography")
    cheap = make_vendor(db_session, category, "Budget Clicks", status=ApprovalStatus.APPROVED,
                        starting_price=Decimal("15000"), service_areas=["Yellareddy"])
    pricey = make_vendor(db_session, category, "Royal Frames", status=ApprovalStatus.APPROVED,
                         starting_price=Decimal("80000"), location="Nizamabad")
    no_price = make_vendor(db_session, category, "Ask Us Studio", status=ApprovalStatus.APPROVED)

    assert public_slugs(db_client, q="royal") == [pricey.slug]
    assert public_slugs(db_client, location="yellareddy") == [cheap.slug]
    assert public_slugs(db_client, location="nizamabad") == [pricey.slug]
    assert public_slugs(db_client, min_price=20000) == [pricey.slug]
    assert public_slugs(db_client, max_price=20000) == [cheap.slug]
    assert public_slugs(db_client, category="photography", sort="price_low") == [cheap.slug, pricey.slug, no_price.slug]
    assert public_slugs(db_client, q="%") == []
    assert db_client.get(f"{API}/vendors", params={"sort": "bogus"}).status_code == 422


# ---------- Claiming admin-created profiles ----------

def test_claim_code_links_profile_once(client_for: ClientFor, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session))
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    code = admin.post(f"{API}/admin/vendors/{vendor.id}/claim-code").json()["code"]
    assert admin.get(f"{API}/admin/vendors/{vendor.id}").json()["has_pending_claim_code"] is True

    owner_user = make_user(db_session, role=UserRole.VENDOR)
    owner = client_for(owner_user)
    assert owner.post(f"{API}/me/vendor/claim", json={"code": "WRONG-CODE1"}).status_code == 400
    claimed = owner.post(f"{API}/me/vendor/claim", json={"code": code.lower()})
    assert claimed.status_code == 200 and claimed.json()["id"] == vendor.id
    assert owner.get(f"{API}/me/vendor").json()["id"] == vendor.id

    other = client_for(make_user(db_session, role=UserRole.VENDOR))
    assert other.post(f"{API}/me/vendor/claim", json={"code": code}).status_code == 400
    assert admin.post(f"{API}/admin/vendors/{vendor.id}/claim-code").status_code == 400  # already linked


def test_expired_claim_code_rejected(client_for: ClientFor, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session))
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    code = admin.post(f"{API}/admin/vendors/{vendor.id}/claim-code").json()["code"]
    db_session.execute(
        Vendor.__table__.update()
        .where(Vendor.id == vendor.id)
        .values(claim_code_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    )
    owner = client_for(make_user(db_session, role=UserRole.VENDOR))
    assert owner.post(f"{API}/me/vendor/claim", json={"code": code}).status_code == 400
