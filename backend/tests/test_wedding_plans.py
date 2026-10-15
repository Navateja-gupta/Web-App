from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import UserRole
from tests.factories import make_category, make_user

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]
URL = f"{API}/me/wedding-plans"


def test_budget_calculations(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session, "Catering")
    client = client_for(make_user(db_session))
    plan = client.post(URL, json={"event_name": "Wedding", "estimated_budget": 400000, "guest_count": 500}).json()
    assert plan["budget"]["committed"] == 0 and plan["budget"]["remaining"] == 400000

    pid = plan["id"]
    client.post(f"{URL}/{pid}/items", json={"description": "Catering", "category_id": category.id, "estimated_cost": 200000})
    client.post(f"{URL}/{pid}/items", json={"description": "Decoration", "estimated_cost": 100000, "actual_cost": 120000, "status": "paid"})
    plan = client.post(f"{URL}/{pid}/items", json={"description": "Fireworks", "estimated_cost": 50000, "status": "cancelled"}).json()

    budget = plan["budget"]
    assert budget["total_estimated"] == 300000  # cancelled item excluded
    assert budget["total_actual"] == 120000
    assert budget["committed"] == 320000  # 200000 estimate + 120000 actual
    assert budget["remaining"] == 80000
    assert budget["over_budget"] is False
    assert budget["by_status"]["cancelled"] == 1 and budget["item_count"] == 3
    assert next(i for i in plan["items"] if i["description"] == "Catering")["category"]["name"] == "Catering"

    item_id = next(i["id"] for i in plan["items"] if i["description"] == "Catering")
    plan = client.patch(f"{URL}/{pid}/items/{item_id}", json={"actual_cost": 310000}).json()
    assert plan["budget"]["committed"] == 430000
    assert plan["budget"]["remaining"] == -30000 and plan["budget"]["over_budget"] is True


def test_expenses_without_budget_or_vendor(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session))
    pid = client.post(URL, json={"event_name": "Haldi"}).json()["id"]
    plan = client.post(f"{URL}/{pid}/items", json={"description": "Turmeric and flowers", "estimated_cost": 3000}).json()
    assert plan["budget"]["remaining"] is None and plan["budget"]["committed"] == 3000


def test_multiple_events_and_update_delete(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session))
    first = client.post(URL, json={"event_name": "Engagement", "event_date": "2027-02-01"}).json()
    client.post(URL, json={"event_name": "Reception"})
    assert [p["event_name"] for p in client.get(URL).json()] == ["Engagement", "Reception"]

    updated = client.patch(f"{URL}/{first['id']}", json={"location": "Kamareddy", "estimated_budget": 100000}).json()
    assert updated["location"] == "Kamareddy"
    assert client.delete(f"{URL}/{first['id']}").status_code == 204
    assert len(client.get(URL).json()) == 1


def test_plans_are_private(client_for: ClientFor, db_session: Session) -> None:
    owner = client_for(make_user(db_session))
    pid = owner.post(URL, json={"event_name": "Wedding"}).json()["id"]
    stranger = client_for(make_user(db_session))
    assert stranger.get(f"{URL}/{pid}").status_code == 404
    assert stranger.post(f"{URL}/{pid}/items", json={"description": "Hack", "estimated_cost": 1}).status_code == 404
    assert client_for(make_user(db_session, role=UserRole.VENDOR)).get(URL).status_code == 403


def test_invalid_amounts_rejected(client_for: ClientFor, db_session: Session) -> None:
    client = client_for(make_user(db_session))
    assert client.post(URL, json={"event_name": "Wedding", "estimated_budget": -5}).status_code == 422
    pid = client.post(URL, json={"event_name": "Wedding"}).json()["id"]
    assert client.post(f"{URL}/{pid}/items", json={"description": "Hall", "estimated_cost": -1}).status_code == 422
