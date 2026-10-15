from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.main import app


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


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    engine = create_engine(_safe_test_database_url(), pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Each test runs inside a transaction that is rolled back afterwards."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """HTTP client for endpoints that do not touch the database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_client(db_session: Session) -> Generator[TestClient, None, None]:
    """HTTP client whose requests use the isolated test database session."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
