from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from tests.factories import DEFAULT_PASSWORD, make_user

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]


def register_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": "Ravi Kumar",
        "email": "ravi@example.com",
        "phone": "98765 43210",
        "password": "SecurePass1",
    }
    payload.update(overrides)
    return payload


def cookie_header(response, name: str) -> str:  # type: ignore[no-untyped-def]
    for header in response.headers.get_list("set-cookie"):
        if header.startswith(f"{name}="):
            return header
    raise AssertionError(f"cookie {name} not set")


# ---------- Registration ----------

def test_register_customer_sets_cookies_and_hashes_password(db_client: TestClient, db_session: Session) -> None:
    response = db_client.post(f"{API}/auth/register", json=register_payload(email="Ravi@Example.com"))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "customer"
    assert body["email"] == "ravi@example.com"
    assert body["phone"] == "+919876543210"
    assert "password" not in body and "password_hash" not in body

    user = db_session.scalar(select(User).where(User.email == "ravi@example.com"))
    assert user is not None
    assert user.password_hash.startswith("$argon2")
    assert "SecurePass1" not in user.password_hash

    access = cookie_header(response, "access_token").lower()
    refresh = cookie_header(response, "refresh_token").lower()
    assert "httponly" in access and "samesite=lax" in access and "path=/" in access
    assert "httponly" in refresh and f"path={API}/auth" in refresh

    assert db_client.get(f"{API}/auth/me").json()["email"] == "ravi@example.com"


def test_register_vendor_role(db_client: TestClient) -> None:
    response = db_client.post(f"{API}/auth/register", json=register_payload(role="vendor", phone=None))
    assert response.status_code == 201
    assert response.json()["role"] == "vendor"


def test_cannot_self_register_as_admin(db_client: TestClient) -> None:
    response = db_client.post(f"{API}/auth/register", json=register_payload(role="admin"))
    assert response.status_code == 422


def test_duplicate_email_rejected(db_client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="taken@example.com")
    response = db_client.post(f"{API}/auth/register", json=register_payload(email="TAKEN@example.com"))
    assert response.status_code == 409


def test_weak_password_rejected(db_client: TestClient) -> None:
    assert db_client.post(f"{API}/auth/register", json=register_payload(password="short1")).status_code == 422
    assert db_client.post(f"{API}/auth/register", json=register_payload(password="lettersonly")).status_code == 422


def test_invalid_phone_rejected(db_client: TestClient) -> None:
    response = db_client.post(f"{API}/auth/register", json=register_payload(phone="12345"))
    assert response.status_code == 422


def test_registration_is_audited(db_client: TestClient, db_session: Session) -> None:
    user_id = db_client.post(f"{API}/auth/register", json=register_payload()).json()["id"]
    log = db_session.scalar(select(AuditLog).where(AuditLog.entity_id == user_id, AuditLog.action == "user.registered"))
    assert log is not None
    assert "password" not in str(log.details).lower()


# ---------- Login / me / logout ----------

def test_login_success_and_me(db_client: TestClient, db_session: Session) -> None:
    user = make_user(db_session, email="login@example.com")
    response = db_client.post(f"{API}/auth/login", json={"email": "LOGIN@example.com", "password": DEFAULT_PASSWORD})
    assert response.status_code == 200
    assert "access_token" not in response.json()  # tokens only travel in HTTP-only cookies
    assert db_client.get(f"{API}/auth/me").json()["id"] == user.id


def test_login_wrong_password_and_unknown_email_give_same_error(db_client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="known@example.com")
    wrong = db_client.post(f"{API}/auth/login", json={"email": "known@example.com", "password": "WrongPass1"})
    unknown = db_client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": "WrongPass1"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Incorrect email or password"}


def test_inactive_user_cannot_log_in(db_client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="off@example.com", is_active=False)
    response = db_client.post(f"{API}/auth/login", json={"email": "off@example.com", "password": DEFAULT_PASSWORD})
    assert response.status_code == 403


def test_me_requires_authentication(db_client: TestClient) -> None:
    response = db_client.get(f"{API}/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_garbage_token_rejected(db_client: TestClient) -> None:
    response = db_client.get(f"{API}/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_bearer_token_flow_for_swagger_and_postman(db_client: TestClient, db_session: Session) -> None:
    make_user(db_session, email="api@example.com")
    token_response = db_client.post(
        f"{API}/auth/token", data={"username": "api@example.com", "password": DEFAULT_PASSWORD}
    )
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]
    me = db_client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "api@example.com"


def test_logout_clears_session(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session))
    refresh_token = client.cookies.get("refresh_token")
    assert client.post(f"{API}/auth/logout").status_code == 204
    assert client.get(f"{API}/auth/me").status_code == 401
    # The old refresh token can no longer be used.
    replay = client_for().post(f"{API}/auth/refresh", headers={"Cookie": f"refresh_token={refresh_token}"})
    assert replay.status_code == 401


# ---------- Refresh rotation ----------

def test_refresh_rotates_token(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session))
    old_refresh = client.cookies.get("refresh_token")
    response = client.post(f"{API}/auth/refresh")
    assert response.status_code == 200
    assert client.cookies.get("refresh_token") != old_refresh
    assert client.get(f"{API}/auth/me").status_code == 200


def test_refresh_without_cookie_fails(db_client: TestClient) -> None:
    assert db_client.post(f"{API}/auth/refresh").status_code == 401


def test_refresh_token_reuse_outside_grace_revokes_all_sessions(client_for: ClientFor, db_session: Session) -> None:
    from datetime import datetime, timedelta, timezone

    from app.core.security import hash_token
    from app.models.user import RefreshToken

    user = make_user(db_session)
    client = client_for(user)
    stolen = client.cookies.get("refresh_token")
    assert client.post(f"{API}/auth/refresh").status_code == 200
    current = client.cookies.get("refresh_token")

    # Pretend the stolen token was rotated long ago, then replay it.
    old = db_session.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(stolen)))
    old.revoked_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.flush()
    replay = client_for().post(f"{API}/auth/refresh", headers={"Cookie": f"refresh_token={stolen}"})
    assert replay.status_code == 401

    # The legitimate session's refresh token is now revoked too.
    legit = client_for().post(f"{API}/auth/refresh", headers={"Cookie": f"refresh_token={current}"})
    assert legit.status_code == 401


# ---------- Profile and password ----------

def test_update_profile(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session))
    response = client.patch(f"{API}/auth/me", json={"full_name": "  New   Name ", "phone": "+91 91234 56789"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "New Name"
    assert response.json()["phone"] == "+919123456789"


def test_user_cannot_change_own_role_via_profile(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session))
    response = client.patch(f"{API}/auth/me", json={"role": "admin"})
    assert response.status_code == 200
    assert response.json()["role"] == "customer"


def test_change_password_invalidates_old_tokens(client_for: ClientFor, db_session: Session) -> None:
    user = make_user(db_session)
    other_device = client_for(user)
    client = client_for(user)
    old_access = other_device.cookies.get("access_token")

    # iat has whole-second precision; make sure the change happens in a later second.
    import time
    time.sleep(1.1)

    response = client.post(
        f"{API}/auth/change-password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": "BrandNew123"},
    )
    assert response.status_code == 204
    assert client.get(f"{API}/auth/me").status_code == 200  # this browser stays signed in
    assert other_device.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {old_access}"}).status_code == 401
    assert other_device.post(f"{API}/auth/refresh").status_code == 401

    relogin = client_for().post(f"{API}/auth/login", json={"email": user.email, "password": "BrandNew123"})
    assert relogin.status_code == 200


def test_change_password_requires_current_password(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session))
    response = client.post(
        f"{API}/auth/change-password", json={"current_password": "WrongPass1", "new_password": "BrandNew123"}
    )
    assert response.status_code == 400


# ---------- Rate limiting ----------

def test_login_rate_limited(db_client: TestClient) -> None:
    payload = {"email": "nobody@example.com", "password": "WrongPass1"}
    statuses = [db_client.post(f"{API}/auth/login", json=payload).status_code for _ in range(settings.LOGIN_RATE_LIMIT)]
    assert set(statuses) == {401}
    blocked = db_client.post(f"{API}/auth/login", json=payload)
    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers


def test_admin_role_is_preserved_on_login(client_for: ClientFor, db_session: Session) -> None:
    admin = make_user(db_session, role=UserRole.ADMIN)
    assert client_for(admin).get(f"{API}/auth/me").json()["role"] == "admin"
