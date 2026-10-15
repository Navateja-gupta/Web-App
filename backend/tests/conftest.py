from collections.abc import Callable, Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, settings
from app.core.rate_limit import reset_all_limiters
from app.db.session import get_db
from app.main import app
from app.models.user import User
from tests.factories import DEFAULT_PASSWORD

API = settings.API_V1_PREFIX


def _safe_test_database_url() -> str:
    """Return TEST_DATABASE_URL, refusing anything that could be the dev database."""
    url = settings.TEST_DATABASE_URL
    if not url:
        pytest.exit("TEST_DATABASE_URL is not set in backend/.env", returncode=1)
    test_db = make_url(url).database or ""
    dev_db = make_url(settings.DATABASE_URL).database or ""
    if not test_db.endswith("_test") or test_db == dev_db:
        pytest.exit(
            f"Refusing to run tests against database '{test_db}'. "
            "TEST_DATABASE_URL must point to a separate database whose name ends with '_test'.",
            returncode=1,
        )
    return url


def _migrate_test_database(url: str) -> None:
    """Rebuild the test schema from migrations (also exercises every downgrade)."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    url = _safe_test_database_url()
    _migrate_test_database(url)
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Each test runs inside a transaction that is rolled back afterwards.

    Service-level commit()/rollback() calls only touch a SAVEPOINT inside it.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> Generator[None, None, None]:
    reset_all_limiters()
    yield
    reset_all_limiters()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """HTTP client for endpoints that do not touch the database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def app_with_db(db_session: Session) -> Generator[FastAPI, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def db_client(app_with_db: FastAPI) -> Generator[TestClient, None, None]:
    """HTTP client whose requests use the isolated test database session."""
    with TestClient(app_with_db) as test_client:
        yield test_client


@pytest.fixture
def client_for(app_with_db: FastAPI) -> Callable[..., TestClient]:
    """Create a separate client (own cookie jar), optionally logged in as `user`."""

    def _make(user: User | None = None, password: str = DEFAULT_PASSWORD) -> TestClient:
        test_client = TestClient(app_with_db)
        if user is not None:
            response = test_client.post(f"{API}/auth/login", json={"email": user.email, "password": password})
            assert response.status_code == 200, response.text
        return test_client

    return _make
