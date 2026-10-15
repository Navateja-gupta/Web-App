from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.main import app

API = settings.API_V1_PREFIX


def test_health_ok(client: TestClient) -> None:
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == settings.APP_NAME


def test_database_connectivity(db_session: Session) -> None:
    assert db_session.execute(text("SELECT 1")).scalar_one() == 1


def test_health_db_ok(db_client: TestClient) -> None:
    response = db_client.get(f"{API}/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_health_db_unavailable_returns_safe_503() -> None:
    # Nothing listens on port 1; the short timeout keeps the test fast on Windows,
    # where refused connections are retried before failing.
    bad_engine = create_engine(
        "postgresql+psycopg://nobody:secret@127.0.0.1:1/nowhere",
        connect_args={"connect_timeout": 1},
    )

    def _broken_db() -> Generator[Session, None, None]:
        session = Session(bind=bad_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _broken_db
    try:
        with TestClient(app) as test_client:
            response = test_client.get(f"{API}/health/db")
    finally:
        app.dependency_overrides.clear()
        bad_engine.dispose()

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert "secret" not in response.text


def test_cors_allows_configured_frontend_origin(client: TestClient) -> None:
    origin = settings.cors_origins[0]
    response = client.options(
        f"{API}/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
