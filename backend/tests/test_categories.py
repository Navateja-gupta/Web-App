from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.enums import ApprovalStatus, UserRole
from tests.factories import make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]


def test_admin_adds_new_category_without_code_changes(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    response = admin.post(f"{API}/admin/categories", json={"name": "  Mehendi   Artists ", "icon": "🌿"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Mehendi Artists"
    assert body["slug"] == "mehendi-artists"

    public = db_client.get(f"{API}/categories").json()
    assert "mehendi-artists" in [c["slug"] for c in public]
    assert db_client.get(f"{API}/categories/mehendi-artists").json()["vendor_count"] == 0

    log = db_session.scalar(select(AuditLog).where(AuditLog.action == "category.created"))
    assert log is not None and log.entity_id == body["id"]


def test_duplicate_category_name_rejected_case_insensitive(client_for: ClientFor, db_session: Session) -> None:
    make_category(db_session, "Photography")
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    assert admin.post(f"{API}/admin/categories", json={"name": "PHOTOGRAPHY"}).status_code == 409


def test_only_admins_manage_categories(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    assert db_client.post(f"{API}/admin/categories", json={"name": "Priests"}).status_code == 401
    for role in (UserRole.CUSTOMER, UserRole.VENDOR):
        client = client_for(make_user(db_session, role=role))
        assert client.post(f"{API}/admin/categories", json={"name": "Priests"}).status_code == 403
        assert client.get(f"{API}/admin/categories").status_code == 403


def test_vendor_count_includes_only_approved_active_vendors(db_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session, "Catering")
    make_vendor(db_session, category, status=ApprovalStatus.APPROVED)
    make_vendor(db_session, category, status=ApprovalStatus.APPROVED)
    make_vendor(db_session, category, status=ApprovalStatus.PENDING)
    make_vendor(db_session, category, status=ApprovalStatus.REJECTED)
    make_vendor(db_session, category, status=ApprovalStatus.APPROVED, is_active=False)
    assert db_client.get(f"{API}/categories/catering").json()["vendor_count"] == 2


def test_deactivated_category_hidden_with_its_vendors(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    category = make_category(db_session, "DJ")
    make_vendor(db_session, category, status=ApprovalStatus.APPROVED)
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))

    response = admin.patch(f"{API}/admin/categories/{category.id}", json={"is_active": False})
    assert response.status_code == 200 and response.json()["is_active"] is False

    assert "dj" not in [c["slug"] for c in db_client.get(f"{API}/categories").json()]
    assert db_client.get(f"{API}/categories/dj").status_code == 404
    assert db_client.get(f"{API}/vendors", params={"category": "dj"}).json()["total"] == 0
    # Still visible to the admin, with history intact.
    assert "dj" in [c["slug"] for c in admin.get(f"{API}/admin/categories").json()]


def test_rename_keeps_slug(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session, "Decor")
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    body = admin.patch(f"{API}/admin/categories/{category.id}", json={"name": "Event Decorators"}).json()
    assert body["name"] == "Event Decorators" and body["slug"] == "decor"


def test_cannot_delete_category_with_vendors(client_for: ClientFor, db_session: Session) -> None:
    used = make_category(db_session, "Used")
    make_vendor(db_session, used)
    empty = make_category(db_session, "Empty")
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    assert admin.delete(f"{API}/admin/categories/{used.id}").status_code == 409
    assert admin.delete(f"{API}/admin/categories/{empty.id}").status_code == 204
    assert admin.delete(f"{API}/admin/categories/{empty.id}").status_code == 404
