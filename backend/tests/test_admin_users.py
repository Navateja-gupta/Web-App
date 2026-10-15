from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.enums import UserRole
from tests.factories import make_user

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]


def test_anonymous_cannot_list_users(db_client: TestClient) -> None:
    assert db_client.get(f"{API}/admin/users").status_code == 401


def test_customer_and_vendor_cannot_list_users(client_for: ClientFor, db_session: Session) -> None:
    for role in (UserRole.CUSTOMER, UserRole.VENDOR):
        response = client_for(make_user(db_session, role=role)).get(f"{API}/admin/users")
        assert response.status_code == 403


def test_admin_lists_and_filters_users(client_for: ClientFor, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    make_user(db_session, role=UserRole.CUSTOMER, full_name="Anjali Reddy")
    make_user(db_session, role=UserRole.VENDOR, full_name="Vendor Person")
    client = client_for(admin)

    customers = client.get(f"{API}/admin/users", params={"role": "customer"}).json()
    assert customers["total"] >= 1
    assert all(u["role"] == "customer" for u in customers["items"])

    search = client.get(f"{API}/admin/users", params={"search": "anjali"}).json()
    assert [u["full_name"] for u in search["items"]] == ["Anjali Reddy"]


def test_search_treats_wildcards_literally(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session, role=UserRole.ADMIN))
    assert client.get(f"{API}/admin/users", params={"search": "%"}).json()["total"] == 0


def test_pagination(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session, role=UserRole.ADMIN))
    for _ in range(3):
        make_user(db_session, role=UserRole.CUSTOMER)
    page = client.get(f"{API}/admin/users", params={"role": "customer", "size": 2, "page": 1}).json()
    assert len(page["items"]) == 2
    assert page["pages"] == 2
    assert client.get(f"{API}/admin/users", params={"size": 500}).status_code == 422


def test_admin_deactivates_user_and_their_session_ends(client_for: ClientFor, db_session: Session) -> None:
    admin_client = client_for(make_user(db_session, role=UserRole.ADMIN))
    customer = make_user(db_session)
    customer_client = client_for(customer)
    assert customer_client.get(f"{API}/auth/me").status_code == 200

    response = admin_client.patch(f"{API}/admin/users/{customer.id}", json={"is_active": False})
    assert response.status_code == 200 and response.json()["is_active"] is False
    assert customer_client.get(f"{API}/auth/me").status_code == 401

    log = db_session.scalar(select(AuditLog).where(AuditLog.action == "user.deactivated"))
    assert log is not None and log.entity_id == customer.id


def test_admin_cannot_deactivate_self(client_for: ClientFor, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    response = client_for(admin).patch(f"{API}/admin/users/{admin.id}", json={"is_active": False})
    assert response.status_code == 400


def test_customer_cannot_deactivate_users(client_for: ClientFor, db_session: Session) -> None:
    victim = make_user(db_session)
    response = client_for(make_user(db_session)).patch(f"{API}/admin/users/{victim.id}", json={"is_active": False})
    assert response.status_code == 403


def test_deactivate_unknown_user_returns_404(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session, role=UserRole.ADMIN))
    assert client.patch(f"{API}/admin/users/999999", json={"is_active": False}).status_code == 404
