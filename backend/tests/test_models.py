"""Schema-level guarantees enforced by PostgreSQL itself (not just by the API)."""

from decimal import Decimal

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import ApprovalStatus, PricingType, UserRole
from app.models.package import VendorPackage
from app.models.shortlist import CustomerShortlist
from tests.factories import make_category, make_user, make_vendor

EXPECTED_TABLES = {
    "users", "refresh_tokens", "service_categories", "vendors", "vendor_packages", "vendor_portfolio",
    "vendor_availability", "customer_shortlists", "quotation_requests", "quotations", "wedding_plans",
    "wedding_plan_items", "bookings", "reviews", "audit_logs",
}


def test_migrations_create_all_tables(test_engine: Engine) -> None:
    assert EXPECTED_TABLES <= set(inspect(test_engine).get_table_names())


def test_new_vendor_defaults_to_pending_and_active(db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session))
    db_session.refresh(vendor)
    assert vendor.approval_status == ApprovalStatus.PENDING
    assert vendor.is_active is True
    assert vendor.is_verified is False
    assert vendor.service_areas == []


def test_duplicate_vendor_name_in_same_category_rejected_case_insensitive(db_session: Session) -> None:
    category = make_category(db_session)
    make_vendor(db_session, category, "Lakshmi Studio")
    with pytest.raises(IntegrityError), db_session.begin_nested():
        make_vendor(db_session, category, "LAKSHMI studio")


def test_same_vendor_name_allowed_in_different_categories(db_session: Session) -> None:
    make_vendor(db_session, make_category(db_session), "Sri Events")
    make_vendor(db_session, make_category(db_session), "Sri Events")


def test_duplicate_category_slug_rejected(db_session: Session) -> None:
    make_category(db_session, "Photography")
    with pytest.raises(IntegrityError), db_session.begin_nested():
        make_category(db_session, "Photography")


def test_duplicate_user_email_rejected(db_session: Session) -> None:
    make_user(db_session, email="same@example.com")
    with pytest.raises(IntegrityError), db_session.begin_nested():
        make_user(db_session, email="same@example.com")


def test_invalid_role_rejected_by_database(db_session: Session) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text(
                "INSERT INTO users (full_name, email, password_hash, role) "
                "VALUES ('X', 'x@example.com', 'h', 'superuser')"
            )
        )


def test_uppercase_email_rejected_by_database(db_session: Session) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text(
                "INSERT INTO users (full_name, email, password_hash, role) "
                "VALUES ('X', 'Upper@Example.com', 'h', 'customer')"
            )
        )


def test_shortlist_is_unique_per_customer_and_vendor(db_session: Session) -> None:
    customer = make_user(db_session, role=UserRole.CUSTOMER)
    vendor = make_vendor(db_session, make_category(db_session))
    db_session.add(CustomerShortlist(customer_id=customer.id, vendor_id=vendor.id))
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(CustomerShortlist(customer_id=customer.id, vendor_id=vendor.id))
        db_session.flush()


def test_package_price_required_unless_quote_on_request(db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session))
    db_session.add(VendorPackage(vendor_id=vendor.id, name="Custom", pricing_type=PricingType.QUOTE_ON_REQUEST))
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(VendorPackage(vendor_id=vendor.id, name="Basic", pricing_type=PricingType.FIXED))
        db_session.flush()


def test_package_price_range_must_be_ordered(db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session))
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            VendorPackage(
                vendor_id=vendor.id,
                name="Range",
                pricing_type=PricingType.STARTING_FROM,
                price=Decimal("50000"),
                price_max=Decimal("40000"),
            )
        )
        db_session.flush()


def test_negative_starting_price_rejected(db_session: Session) -> None:
    vendor = make_vendor(db_session, make_category(db_session))
    vendor.starting_price = Decimal("-1")
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.flush()
