from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ApprovalStatus, BookingStatus, UserRole
from tests.factories import make_booking, make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]


def test_stats_reflect_database(client_for: ClientFor, db_session: Session) -> None:
    category = make_category(db_session, "Photography")
    vendor = make_vendor(db_session, category, status=ApprovalStatus.APPROVED)
    make_vendor(db_session, category)
    customer = make_user(db_session)
    make_booking(db_session, customer, vendor, status=BookingStatus.CONFIRMED)
    admin = client_for(make_user(db_session, role=UserRole.ADMIN))

    stats = admin.get(f"{API}/admin/stats").json()
    assert stats["vendors_by_status"]["approved"] == 1 and stats["vendors_by_status"]["pending"] == 1
    assert stats["bookings_by_status"]["confirmed"] == 1
    assert stats["confirmed_booking_value"] == 50000.0
    assert {"category": "Photography", "vendors": 1} in stats["live_vendors_by_category"]
    assert stats["users_by_role"]["customer"] >= 1


def test_admin_endpoints_require_admin(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    paths = ["/admin/stats", "/admin/audit-logs", "/admin/quotation-requests", "/admin/bookings", "/admin/reviews", "/admin/reports"]
    for path in paths:
        assert db_client.get(f"{API}{path}").status_code == 401, path
    for role in (UserRole.CUSTOMER, UserRole.VENDOR):
        client = client_for(make_user(db_session, role=role))
        for path in paths:
            assert client.get(f"{API}{path}").status_code == 403, (role, path)


def test_audit_log_viewer(client_for: ClientFor, db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session))
    admin_user = make_user(db_session, role=UserRole.ADMIN, full_name="Admin Person")
    admin = client_for(admin_user)
    admin.post(f"{API}/admin/vendors/{vendor.id}/approve")

    logs = admin.get(f"{API}/admin/audit-logs", params={"action": "vendor.", "entity_type": "vendor"}).json()
    entry = next(item for item in logs["items"] if item["entity_id"] == vendor.id)
    assert entry["action"] == "vendor.approved"
    assert entry["actor"]["full_name"] == "Admin Person"
    assert "password" not in str(logs).lower()
