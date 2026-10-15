from collections.abc import Callable
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ApprovalStatus, UserRole
from tests.factories import make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]
URL = f"{API}/me/vendor/availability"


def test_set_upsert_list_and_clear(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session, role=UserRole.VENDOR)
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED, owner=owner)
    client = client_for(owner)
    day = date.today() + timedelta(days=10)

    assert client.put(f"{URL}/{day}", json={"availability_status": "available"}).status_code == 200
    updated = client.put(f"{URL}/{day}", json={"availability_status": "booked", "notes": "Offline booking"})
    assert updated.json() == {"date": day.isoformat(), "availability_status": "booked", "notes": "Offline booking"}

    listed = client.get(URL, params={"start": date.today().isoformat(), "end": (day + timedelta(days=1)).isoformat()}).json()
    assert len(listed) == 1  # one record per date, never duplicated

    public = db_client.get(f"{API}/vendors/{vendor.slug}/availability").json()
    assert public[0]["availability_status"] == "booked"

    assert client.delete(f"{URL}/{day}").status_code == 204
    assert client.get(URL).json() == []


def test_past_dates_and_bad_ranges_rejected(client_for: ClientFor, db_session: Session) -> None:
    owner = make_user(db_session, role=UserRole.VENDOR)
    make_vendor(db_session, make_category(db_session), owner=owner)
    client = client_for(owner)
    yesterday = date.today() - timedelta(days=1)
    assert client.put(f"{URL}/{yesterday}", json={"availability_status": "available"}).status_code == 400
    assert client.put(f"{URL}/{date.today()}", json={"availability_status": "maybe"}).status_code == 422
    assert client.get(URL, params={"start": "2027-01-10", "end": "2027-01-01"}).status_code == 400
    assert client.get(URL, params={"start": "2027-01-01", "end": "2028-06-01"}).status_code == 400
