"""Enquiries (quotation requests) and vendor quotations.

Accepting a quotation creates a booking in `requested` state. The vendor must still
confirm it, so a quotation never becomes a confirmed booking on its own.
"""

from datetime import date

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.dependencies.pagination import PageParams
from app.models.booking import Booking
from app.models.enums import BookingStatus, QuotationRequestStatus, QuotationStatus
from app.models.quotation import Quotation, QuotationRequest
from app.models.user import User
from app.models.vendor import Vendor
from app.models.wedding_plan import WeddingPlan
from app.schemas.quotation import QuotationCreate, QuotationRequestCreate
from app.services import notify_events
from app.services.audit import record_audit
from app.services.vendors import get_public_vendor_by_id

OPEN_REQUEST = (QuotationRequestStatus.PENDING, QuotationRequestStatus.QUOTED)


def _request_query() -> Select:  # type: ignore[type-arg]
    return (
        select(QuotationRequest)
        .options(
            selectinload(QuotationRequest.vendor).selectinload(Vendor.category),
            selectinload(QuotationRequest.customer),
            selectinload(QuotationRequest.quotations).selectinload(Quotation.vendor).selectinload(Vendor.category),
        )
        .execution_options(populate_existing=True)
    )


def _quotation_query() -> Select:  # type: ignore[type-arg]
    return (
        select(Quotation)
        .join(Quotation.request)
        .options(selectinload(Quotation.vendor).selectinload(Vendor.category), selectinload(Quotation.request))
        .execution_options(populate_existing=True)
    )


def expire_stale_quotations(db: Session) -> None:
    """Quotations past their validity date can no longer be accepted."""
    result = db.execute(
        update(Quotation)
        .where(Quotation.status == QuotationStatus.SENT, Quotation.validity_date < date.today())
        .values(status=QuotationStatus.EXPIRED)
    )
    if result.rowcount:
        db.commit()


def _own_plan(db: Session, customer: User, plan_id: int | None) -> None:
    if plan_id is None:
        return
    plan = db.get(WeddingPlan, plan_id)
    if plan is None or plan.customer_id != customer.id:
        raise NotFoundError("Wedding plan not found")


# ---------- Customer: enquiries ----------

def create_requests(db: Session, customer: User, data: QuotationRequestCreate) -> list[QuotationRequest]:
    """Send one enquiry to each selected vendor, all or nothing."""
    if data.service_date < date.today():
        raise BusinessRuleError("The event date must be today or later")
    _own_plan(db, customer, data.wedding_plan_id)

    vendors = []
    for vendor_id in data.vendor_ids:
        try:
            vendor = get_public_vendor_by_id(db, vendor_id)
        except NotFoundError:
            raise NotFoundError(f"Vendor {vendor_id} is not available")
        duplicate = db.scalar(
            select(QuotationRequest.id).where(
                QuotationRequest.customer_id == customer.id,
                QuotationRequest.vendor_id == vendor.id,
                QuotationRequest.service_date == data.service_date,
                QuotationRequest.status.in_(OPEN_REQUEST),
            )
        )
        if duplicate:
            raise ConflictError(f"You already have an open enquiry with {vendor.business_name} for this date")
        vendors.append(vendor)

    created = []
    for vendor in vendors:
        request = QuotationRequest(
            customer_id=customer.id,
            vendor_id=vendor.id,
            wedding_plan_id=data.wedding_plan_id,
            service_date=data.service_date,
            event_location=data.event_location,
            guest_count=data.guest_count,
            requirements=data.requirements,
            budget=data.budget,
        )
        db.add(request)
        db.flush()
        record_audit(db, actor_id=customer.id, action="quotation_request.created", entity_type="quotation_request",
                     entity_id=request.id, details={"vendor_id": vendor.id})
        notify_events.enquiry_created(db, request, vendor, customer)
        created.append(request.id)
    db.commit()
    return list(db.scalars(_request_query().where(QuotationRequest.id.in_(created)).order_by(QuotationRequest.id)))


def list_customer_requests(db: Session, customer: User, status: QuotationRequestStatus | None = None) -> list[QuotationRequest]:
    expire_stale_quotations(db)
    stmt = _request_query().where(QuotationRequest.customer_id == customer.id)
    if status is not None:
        stmt = stmt.where(QuotationRequest.status == status)
    return list(db.scalars(stmt.order_by(QuotationRequest.created_at.desc(), QuotationRequest.id.desc())))


def get_customer_request(db: Session, customer: User, request_id: int) -> QuotationRequest:
    expire_stale_quotations(db)
    request = db.scalar(
        _request_query().where(QuotationRequest.id == request_id, QuotationRequest.customer_id == customer.id)
    )
    if request is None:
        raise NotFoundError("Enquiry not found")
    return request


def cancel_request(db: Session, customer: User, request_id: int) -> QuotationRequest:
    request = get_customer_request(db, customer, request_id)
    if request.status not in OPEN_REQUEST:
        raise BusinessRuleError("This enquiry is already closed")
    request.status = QuotationRequestStatus.CANCELLED
    db.execute(
        update(Quotation)
        .where(Quotation.quotation_request_id == request.id, Quotation.status == QuotationStatus.SENT)
        .values(status=QuotationStatus.REJECTED)
    )
    record_audit(db, actor_id=customer.id, action="quotation_request.cancelled", entity_type="quotation_request",
                 entity_id=request.id)
    db.commit()
    return get_customer_request(db, customer, request.id)


# ---------- Customer: quotations ----------

def list_customer_quotations(db: Session, customer: User, status: QuotationStatus | None = None) -> list[Quotation]:
    expire_stale_quotations(db)
    stmt = _quotation_query().where(QuotationRequest.customer_id == customer.id)
    if status is not None:
        stmt = stmt.where(Quotation.status == status)
    return list(db.scalars(stmt.order_by(Quotation.created_at.desc(), Quotation.id.desc())))


def _customer_quotation(db: Session, customer: User, quotation_id: int) -> Quotation:
    quotation = db.scalar(
        _quotation_query().where(Quotation.id == quotation_id, QuotationRequest.customer_id == customer.id).with_for_update(of=Quotation)
    )
    if quotation is None:
        raise NotFoundError("Quotation not found")
    return quotation


def accept_quotation(db: Session, customer: User, quotation_id: int) -> Booking:
    """Accept one quotation: closes the enquiry and creates a booking request for the vendor to confirm."""
    expire_stale_quotations(db)
    quotation = _customer_quotation(db, customer, quotation_id)
    request = quotation.request

    if quotation.status != QuotationStatus.SENT:
        raise BusinessRuleError(f"This quotation is {quotation.status.value} and can no longer be accepted")
    if request.status not in OPEN_REQUEST:
        raise BusinessRuleError("This enquiry is closed")
    if request.service_date < date.today():
        raise BusinessRuleError("The event date has already passed")
    try:
        vendor = get_public_vendor_by_id(db, quotation.vendor_id)
    except NotFoundError:
        raise BusinessRuleError("This vendor is not currently accepting bookings on the platform")

    quotation.status = QuotationStatus.ACCEPTED
    db.execute(
        update(Quotation)
        .where(
            Quotation.quotation_request_id == request.id,
            Quotation.id != quotation.id,
            Quotation.status == QuotationStatus.SENT,
        )
        .values(status=QuotationStatus.REJECTED)
    )
    request.status = QuotationRequestStatus.CLOSED
    booking = Booking(
        customer_id=customer.id,
        vendor_id=quotation.vendor_id,
        quotation_id=quotation.id,
        wedding_plan_id=request.wedding_plan_id,
        event_date=request.service_date,
        event_location=request.event_location,
        agreed_amount=quotation.quoted_amount,
        booking_status=BookingStatus.REQUESTED,
    )
    db.add(booking)
    db.flush()
    record_audit(db, actor_id=customer.id, action="quotation.accepted", entity_type="quotation", entity_id=quotation.id)
    record_audit(db, actor_id=customer.id, action="booking.requested", entity_type="booking", entity_id=booking.id,
                 details={"vendor_id": booking.vendor_id, "from_quotation": quotation.id})
    notify_events.booking_requested(db, booking, vendor, customer)
    db.commit()  # all of the above succeed or fail together
    return booking


def reject_quotation(db: Session, customer: User, quotation_id: int) -> Quotation:
    expire_stale_quotations(db)
    quotation = _customer_quotation(db, customer, quotation_id)
    if quotation.status != QuotationStatus.SENT:
        raise BusinessRuleError(f"This quotation is already {quotation.status.value}")
    quotation.status = QuotationStatus.REJECTED
    record_audit(db, actor_id=customer.id, action="quotation.rejected", entity_type="quotation", entity_id=quotation.id)
    db.commit()
    return _customer_quotation(db, customer, quotation.id)


# ---------- Vendor: enquiries and quotations ----------

def list_vendor_enquiries(
    db: Session, vendor: Vendor, params: PageParams, status: QuotationRequestStatus | None = None
) -> tuple[list[QuotationRequest], int]:
    expire_stale_quotations(db)
    stmt = _request_query().where(QuotationRequest.vendor_id == vendor.id)
    if status is not None:
        stmt = stmt.where(QuotationRequest.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(
        stmt.order_by(QuotationRequest.created_at.desc(), QuotationRequest.id.desc()).offset(params.offset).limit(params.size)
    ).all()
    return list(items), total


def get_vendor_enquiry(db: Session, vendor: Vendor, request_id: int) -> QuotationRequest:
    expire_stale_quotations(db)
    request = db.scalar(_request_query().where(QuotationRequest.id == request_id, QuotationRequest.vendor_id == vendor.id))
    if request is None:
        raise NotFoundError("Enquiry not found")
    return request


def decline_enquiry(db: Session, vendor: Vendor, actor: User, request_id: int, reason: str | None) -> QuotationRequest:
    request = get_vendor_enquiry(db, vendor, request_id)
    if request.status not in OPEN_REQUEST:
        raise BusinessRuleError("This enquiry is already closed")
    request.status = QuotationRequestStatus.DECLINED
    request.vendor_response = reason
    db.execute(
        update(Quotation)
        .where(Quotation.quotation_request_id == request.id, Quotation.status == QuotationStatus.SENT)
        .values(status=QuotationStatus.WITHDRAWN)
    )
    record_audit(db, actor_id=actor.id, action="quotation_request.declined", entity_type="quotation_request",
                 entity_id=request.id)
    notify_events.enquiry_declined(db, request, vendor)
    db.commit()
    return get_vendor_enquiry(db, vendor, request.id)


def send_quotation(db: Session, vendor: Vendor, actor: User, request_id: int, data: QuotationCreate) -> QuotationRequest:
    """Send (or revise) a quotation. A revision replaces the vendor's earlier sent quotation."""
    request = get_vendor_enquiry(db, vendor, request_id)
    if request.status not in OPEN_REQUEST:
        raise BusinessRuleError("This enquiry is no longer open")
    if data.validity_date is not None and data.validity_date < date.today():
        raise BusinessRuleError("The validity date must be today or later")

    db.execute(
        update(Quotation)
        .where(Quotation.quotation_request_id == request.id, Quotation.status == QuotationStatus.SENT)
        .values(status=QuotationStatus.WITHDRAWN)
    )
    quotation = Quotation(quotation_request_id=request.id, vendor_id=vendor.id, **data.model_dump())
    db.add(quotation)
    request.status = QuotationRequestStatus.QUOTED
    db.flush()
    record_audit(db, actor_id=actor.id, action="quotation.sent", entity_type="quotation", entity_id=quotation.id,
                 details={"quotation_request_id": request.id})
    notify_events.quotation_received(db, request, quotation, vendor)
    db.commit()
    return get_vendor_enquiry(db, vendor, request.id)


def withdraw_quotation(db: Session, vendor: Vendor, actor: User, quotation_id: int) -> QuotationRequest:
    quotation = db.scalar(
        select(Quotation).where(Quotation.id == quotation_id, Quotation.vendor_id == vendor.id).with_for_update()
    )
    if quotation is None:
        raise NotFoundError("Quotation not found")
    if quotation.status != QuotationStatus.SENT:
        raise BusinessRuleError(f"This quotation is already {quotation.status.value}")
    quotation.status = QuotationStatus.WITHDRAWN
    request = db.get(QuotationRequest, quotation.quotation_request_id)
    if request is not None and request.status == QuotationRequestStatus.QUOTED:
        request.status = QuotationRequestStatus.PENDING
    record_audit(db, actor_id=actor.id, action="quotation.withdrawn", entity_type="quotation", entity_id=quotation.id)
    db.commit()
    return get_vendor_enquiry(db, vendor, quotation.quotation_request_id)


# ---------- Admin ----------

def list_all_enquiries(
    db: Session, params: PageParams, status: QuotationRequestStatus | None = None, vendor_id: int | None = None
) -> tuple[list[QuotationRequest], int]:
    expire_stale_quotations(db)
    stmt = _request_query()
    if status is not None:
        stmt = stmt.where(QuotationRequest.status == status)
    if vendor_id is not None:
        stmt = stmt.where(QuotationRequest.vendor_id == vendor_id)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(
        stmt.order_by(QuotationRequest.created_at.desc(), QuotationRequest.id.desc()).offset(params.offset).limit(params.size)
    ).all()
    return list(items), total
