from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_token
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.notification import Notification
from app.models.password_reset import PasswordResetToken
from tests.factories import DEFAULT_PASSWORD, make_user

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]
NEW_PASSWORD = "FreshStart42"


def token_from(url: str) -> str:
    assert "#token=" in url  # token must be in the fragment, never in the path or query
    return url.split("#token=", 1)[1]


def test_full_admin_assisted_reset(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    user = make_user(db_session, full_name="Lakshmi Devi")
    old_session = client_for(user)

    link = admin.post(f"{API}/admin/users/{user.id}/password-reset-link")
    assert link.status_code == 200, link.text
    body = link.json()
    assert body["user_email"] == user.email
    assert body["reset_url"].startswith(f"{settings.FRONTEND_BASE_URL}/reset-password#token=")
    token = token_from(body["reset_url"])

    # Only the hash is stored.
    stored = db_session.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    assert stored is not None and stored.token_hash == hash_token(token) and token not in stored.token_hash

    assert db_client.post(f"{API}/auth/password-reset/verify", json={"token": token}).json() == {"first_name": "Lakshmi"}
    assert db_client.post(f"{API}/auth/password-reset", json={"token": token, "new_password": NEW_PASSWORD}).status_code == 204

    # Old sessions are signed out, old password stops working, new one works.
    assert old_session.get(f"{API}/auth/me").status_code == 401
    assert client_for().post(f"{API}/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}).status_code == 401
    assert client_for().post(f"{API}/auth/login", json={"email": user.email, "password": NEW_PASSWORD}).status_code == 200

    # One-time use.
    again = db_client.post(f"{API}/auth/password-reset", json={"token": token, "new_password": "Another123"})
    assert again.status_code == 400

    assert db_session.scalar(select(Notification).where(Notification.user_id == user.id, Notification.kind == "account.password_reset"))
    actions = set(db_session.scalars(select(AuditLog.action).where(AuditLog.entity_id == user.id)))
    assert {"user.password_reset_link_created", "user.password_reset"} <= actions


def test_new_link_cancels_previous(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    user = make_user(db_session)
    first = token_from(admin.post(f"{API}/admin/users/{user.id}/password-reset-link").json()["reset_url"])
    second = token_from(admin.post(f"{API}/admin/users/{user.id}/password-reset-link").json()["reset_url"])
    assert db_client.post(f"{API}/auth/password-reset/verify", json={"token": first}).status_code == 400
    assert db_client.post(f"{API}/auth/password-reset/verify", json={"token": second}).status_code == 200


def test_expired_link_rejected(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    user = make_user(db_session)
    token = token_from(admin.post(f"{API}/admin/users/{user.id}/password-reset-link").json()["reset_url"])
    db_session.execute(
        PasswordResetToken.__table__.update()
        .where(PasswordResetToken.user_id == user.id)
        .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    )
    response = db_client.post(f"{API}/auth/password-reset", json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 400 and "expired" in response.json()["detail"]


def test_weak_password_and_bad_token(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    user = make_user(db_session)
    token = token_from(admin.post(f"{API}/admin/users/{user.id}/password-reset-link").json()["reset_url"])
    assert db_client.post(f"{API}/auth/password-reset", json={"token": token, "new_password": "short"}).status_code == 422
    assert db_client.post(f"{API}/auth/password-reset", json={"token": "x" * 40, "new_password": NEW_PASSWORD}).status_code == 400
    # The weak attempt did not use up the link.
    assert db_client.post(f"{API}/auth/password-reset/verify", json={"token": token}).status_code == 200


def test_only_admins_create_links_and_not_for_self_or_inactive(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    admin_user = make_user(db_session, role=UserRole.ADMIN)
    admin = client_for(admin_user)
    target = make_user(db_session)

    assert db_client.post(f"{API}/admin/users/{target.id}/password-reset-link").status_code == 401
    for role in (UserRole.CUSTOMER, UserRole.VENDOR):
        assert client_for(make_user(db_session, role=role)).post(f"{API}/admin/users/{target.id}/password-reset-link").status_code == 403

    assert admin.post(f"{API}/admin/users/{admin_user.id}/password-reset-link").status_code == 400
    inactive = make_user(db_session, is_active=False)
    assert admin.post(f"{API}/admin/users/{inactive.id}/password-reset-link").status_code == 400
    assert admin.post(f"{API}/admin/users/999999/password-reset-link").status_code == 404


def test_link_stops_working_if_account_deactivated(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))
    user = make_user(db_session)
    token = token_from(admin.post(f"{API}/admin/users/{user.id}/password-reset-link").json()["reset_url"])
    admin.patch(f"{API}/admin/users/{user.id}", json={"is_active": False})
    assert db_client.post(f"{API}/auth/password-reset", json={"token": token, "new_password": NEW_PASSWORD}).status_code == 400
