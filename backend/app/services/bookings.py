"""Bookings and their allowed status transitions.

    requested ──confirm (vendor/admin)──► confirmed ──complete (vendor/admin, on/after event)──► completed
        │  └──reject (vendor/admin)──► rejected     │
        └──────────cancel (customer/vendor/admin)───┴──► cancelled
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError, PermissionDeniedError
from app.dependencies.pagination import PageParams
from app.models.booking import Booking
from app.models.enums import BookingStatus, PlanItemStatus, UserRole
from app.models.package import VendorPackage
from app.models.user import User
from app.models.vendor import Vendor
from app.models.wedding_plan import WeddingPlan, WeddingPlanItem
from app.schemas.booking import BookingCreate
from app.services.audit import record_audit
from app.services.vendors import get_public_vendor_by_id

OPEN_STATUSES = (BookingStatus.REQUESTED, BookingStatus.CONFIRMED)

# action -> (allowed current statuses, new status, roles allowed to perform it)
TRANSITIONS: dict[str, tuple[set[BookingStatus], BookingStatus, set[UserRole]]] = {
    "confirm": ({BookingStatus.REQUESTED}, BookingStatus.CONFIRMED, {UserRole.VENDOR, UserRole.ADMIN}),
    "reject": ({BookingStatus.REQUESTED}, BookingStatus.REJECTED, {UserRole.VENDOR, UserRole.ADMIN}),
    "cancel": (set(OPEN_STATUSES), BookingStatus.CANCELLED, {UserRole.CUSTOMER, UserRole.VENDOR, UserRole.ADMIN}),
    "complete": ({BookingStatus.CONFIRMED}, BookingStatus.COMPLETED, {UserRole.VENDOR, UserRole.ADMIN}),
}


def _query() -> Select:  # type: ignore[type-arg]
    return (
        select(Booking)
        .options(
            selectinload(Booking.vendor).selectinload(Vendor.category),
            selectinload(Booking.customer),
            selectinload(Booking.package),
            selectinload(Booking.review),
        )
        .execution_options(populate_existing=True)
    )


def get_booking(db: Session, booking_id: int, *, customer: User | None = None, vendor: Vendor | None = None) -> Booking:
    """Load a booking scoped to its customer or vendor (admins pass neither)."""
    stmt = _query().where(Booking.id == booking_id)
    if customer is not None:
        stmt = stmt.where(Booking.customer_id == customer.id)
    if vendor is not None:
        stmt = stmt.where(Booking.vendor_id == vendor.id)
    booking = db.scalar(stmt)
    if booking is None:
        raise NotFoundError("Booking not found")
    return booking


def list_bookings(
    db: Session,
    params: PageParams,
    *,
    customer: User | None = None,
    vendor: Vendor | None = None,
    status: BookingStatus | None = None,
    vendor_id: int | None = None,
) -> tuple[list[Booking], int]:
    stmt = _query()
    if customer is not None:
        stmt = stmt.where(Booking.customer_id == customer.id)
    if vendor is not None:
        stmt = stmt.where(Booking.vendor_id == vendor.id)
    if vendor_id is not None:
        stmt = stmt.where(Booking.vendor_id == vendor_id)
    if status is not None:
        stmt = stmt.where(Booking.booking_status == status)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.order_by(Booking.event_date.asc(), Booking.id.asc()).offset(params.offset).limit(params.size)).all()
    return list(items), total


def create_booking(db: Session, customer: User, data: BookingCreate) -> Booking:
    """Direct booking request (e.g. for a published package). The vendor must confirm it."""
    vendor = get_public_vendor_by_id(db, data.vendor_id)
    if data.event_date < date.today():
        raise BusinessRuleError("The event date must be today or later")
    if data.package_id is not None:
        package = db.get(VendorPackage, data.package_id)
        if package is None or package.vendor_id != vendor.id or not package.is_active:
            raise NotFoundError("Package not found for this vendor")
    if data.wedding_plan_id is not None:
        plan = db.get(WeddingPlan, data.wedding_plan_id)
        if plan is None or plan.customer_id != customer.id:
            raise NotFoundError("Wedding plan not found")
    duplicate = db.scalar(
        select(Booking.id).where(
            Booking.customer_id == customer.id,
            Booking.vendor_id == vendor.id,
            Booking.event_date == data.event_date,
            Booking.booking_status.in_(OPEN_STATUSES),
        )
    )
    if duplicate:
        raise ConflictError("You already have a booking request with this vendor for this date")

    booking = Booking(customer_id=customer.id, **data.model_dump())
    db.add(booking)
    db.flush()
    record_audit(db, actor_id=customer.id, action="booking.requested", entity_type="booking", entity_id=booking.id,
                 details={"vendor_id": vendor.id})
    db.commit()
    return get_booking(db, booking.id)


def change_status(
    db: Session,
    booking: Booking,
    action: str,
    actor: User,
    *,
    reason: str | None = None,
    agreed_amount: Decimal | None = None,
) -> Booking:
    allowed_from, target, roles = TRANSITIONS[action]
    if actor.role not in roles:
        raise PermissionDeniedError("You are not allowed to perform this action")
    if booking.booking_status not in allowed_from:
        raise BusinessRuleError(f"Cannot {action} a booking that is {booking.booking_status.value}")

    now = datetime.now(timezone.utc)
    previous = booking.booking_status

    if action == "confirm":
        if booking.event_date < date.today():
            raise BusinessRuleError("The event date has already passed")
        amount = agreed_amount if agreed_amount is not None else booking.agreed_amount
        if amount is None:
            raise BusinessRuleError("Enter the agreed amount to confirm this booking")
        booking.agreed_amount = amount
        booking.confirmed_at = now
        if booking.wedding_plan_id is not None:
            # Keep the customer's budget in sync with the confirmed booking.
            db.add(
                WeddingPlanItem(
                    wedding_plan_id=booking.wedding_plan_id,
                    category_id=booking.vendor.category_id,
                    vendor_id=booking.vendor_id,
                    package_id=booking.package_id,
                    description=f"{booking.vendor.business_name} (booking #{booking.id})",
                    estimated_cost=amount,
                    status=PlanItemStatus.BOOKED,
                )
            )
    elif action in ("reject", "cancel"):
        if not reason:
            raise BusinessRuleError("Please give a reason")
        booking.cancelled_at = now
        booking.cancelled_by_id = actor.id
        booking.cancellation_reason = reason
    elif action == "complete":
        if booking.event_date > date.today():
            raise BusinessRuleError("A booking can only be completed on or after the event date")
        booking.completed_at = now

    booking.booking_status = target
    record_audit(db, actor_id=actor.id, action=f"booking.{target.value}", entity_type="booking", entity_id=booking.id,
                 details={"from": previous.value, "to": target.value, "reason": reason})
    db.commit()
    return get_booking(db, booking.id)
