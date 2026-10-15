"""Customer workspace: enquiries, quotations, bookings, reviews and wedding plans.

Every query is scoped to the signed-in customer, so another customer's id returns 404.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.dependencies.auth import require_customer
from app.dependencies.pagination import PageParams, get_page_params
from app.models.enums import BookingStatus, QuotationRequestStatus, QuotationStatus
from app.models.user import User
from app.models.wedding_plan import WeddingPlan
from app.schemas.booking import BookingCreate, BookingRead, BookingReason
from app.schemas.common import Page
from app.schemas.quotation import QuotationRead, QuotationRequestCreate, QuotationRequestRead
from app.schemas.review import ReviewCreate
from app.schemas.wedding_plan import (
    PlanItemCreate,
    PlanItemUpdate,
    WeddingPlanCreate,
    WeddingPlanRead,
    WeddingPlanSummary,
    WeddingPlanUpdate,
)
from app.services import bookings as booking_service
from app.services import quotations as quotation_service
from app.services import reviews as review_service
from app.services import wedding_plans as plan_service

router = APIRouter(prefix="/me", tags=["customer: planning"])

enquiry_rate_limit = rate_limit(30, 3600)

_PLAN_FIELDS = ("id", "event_name", "event_date", "location", "estimated_budget", "guest_count", "created_at", "updated_at")


def plan_read(plan: WeddingPlan) -> WeddingPlanRead:
    data = {f: getattr(plan, f) for f in _PLAN_FIELDS}
    data.update(items=plan.items, budget=plan_service.budget_summary(plan))
    return WeddingPlanRead.model_validate(data, from_attributes=True)


def plan_summary(plan: WeddingPlan) -> WeddingPlanSummary:
    data = {f: getattr(plan, f) for f in _PLAN_FIELDS}
    data["budget"] = plan_service.budget_summary(plan)
    return WeddingPlanSummary.model_validate(data)


# ---------- Enquiries ----------

@router.post(
    "/quotation-requests",
    response_model=list[QuotationRequestRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enquiry_rate_limit)],
)
def create_quotation_requests(
    data: QuotationRequestCreate, customer: User = Depends(require_customer), db: Session = Depends(get_db)
):  # type: ignore[no-untyped-def]
    """Send your requirements to one or more vendors (one enquiry per vendor)."""
    return quotation_service.create_requests(db, customer, data)


@router.get("/quotation-requests", response_model=list[QuotationRequestRead])
def list_quotation_requests(
    status_filter: QuotationRequestStatus | None = Query(default=None, alias="status"),
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
):  # type: ignore[no-untyped-def]
    return quotation_service.list_customer_requests(db, customer, status_filter)


@router.get("/quotation-requests/{request_id}", response_model=QuotationRequestRead)
def get_quotation_request(request_id: int, customer: User = Depends(require_customer), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return quotation_service.get_customer_request(db, customer, request_id)


@router.post("/quotation-requests/{request_id}/cancel", response_model=QuotationRequestRead)
def cancel_quotation_request(request_id: int, customer: User = Depends(require_customer), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return quotation_service.cancel_request(db, customer, request_id)


# ---------- Quotations ----------

@router.get("/quotations", response_model=list[QuotationRead])
def list_quotations(
    status_filter: QuotationStatus | None = Query(default=None, alias="status"),
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
):  # type: ignore[no-untyped-def]
    """All quotations you have received, for side-by-side comparison."""
    return quotation_service.list_customer_quotations(db, customer, status_filter)


@router.post("/quotations/{quotation_id}/accept", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def accept_quotation(quotation_id: int, customer: User = Depends(require_customer), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    """Accept a quotation. This creates a booking request that the vendor still has to confirm."""
    booking = quotation_service.accept_quotation(db, customer, quotation_id)
    return booking_service.get_booking(db, booking.id, customer=customer)


@router.post("/quotations/{quotation_id}/reject", response_model=QuotationRead)
def reject_quotation(quotation_id: int, customer: User = Depends(require_customer), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return quotation_service.reject_quotation(db, customer, quotation_id)


# ---------- Bookings ----------

@router.post("/bookings", response_model=BookingRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(enquiry_rate_limit)])
def create_booking(data: BookingCreate, customer: User = Depends(require_customer), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    """Request a booking directly. It stays `requested` until the vendor confirms."""
    return booking_service.create_booking(db, customer, data)


@router.get("/bookings", response_model=Page[BookingRead])
def list_bookings(
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    params: PageParams = Depends(get_page_params),
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> Page[BookingRead]:
    items, total = booking_service.list_bookings(db, params, customer=customer, status=status_filter)
    return Page[BookingRead].build([BookingRead.model_validate(b) for b in items], total, params.page, params.size)


@router.get("/bookings/{booking_id}", response_model=BookingRead)
def get_booking(booking_id: int, customer: User = Depends(require_customer), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return booking_service.get_booking(db, booking_id, customer=customer)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingRead)
def cancel_booking(
    booking_id: int, data: BookingReason, customer: User = Depends(require_customer), db: Session = Depends(get_db)
):  # type: ignore[no-untyped-def]
    booking = booking_service.get_booking(db, booking_id, customer=customer)
    return booking_service.change_status(db, booking, "cancel", customer, reason=data.reason)


@router.post("/bookings/{booking_id}/review", status_code=status.HTTP_201_CREATED)
def review_booking(
    booking_id: int, data: ReviewCreate, customer: User = Depends(require_customer), db: Session = Depends(get_db)
) -> dict[str, int]:
    """Review the vendor after a completed booking (one review per booking)."""
    review = review_service.create_review(db, customer, booking_id, data)
    return {"id": review.id, "rating": review.rating}


# ---------- Wedding plans & budget ----------

@router.get("/wedding-plans", response_model=list[WeddingPlanSummary])
def list_wedding_plans(customer: User = Depends(require_customer), db: Session = Depends(get_db)) -> list[WeddingPlanSummary]:
    return [plan_summary(p) for p in plan_service.list_plans(db, customer)]


@router.post("/wedding-plans", response_model=WeddingPlanRead, status_code=status.HTTP_201_CREATED)
def create_wedding_plan(
    data: WeddingPlanCreate, customer: User = Depends(require_customer), db: Session = Depends(get_db)
) -> WeddingPlanRead:
    return plan_read(plan_service.create_plan(db, customer, data))


@router.get("/wedding-plans/{plan_id}", response_model=WeddingPlanRead)
def get_wedding_plan(plan_id: int, customer: User = Depends(require_customer), db: Session = Depends(get_db)) -> WeddingPlanRead:
    return plan_read(plan_service.get_plan(db, customer, plan_id))


@router.patch("/wedding-plans/{plan_id}", response_model=WeddingPlanRead)
def update_wedding_plan(
    plan_id: int, data: WeddingPlanUpdate, customer: User = Depends(require_customer), db: Session = Depends(get_db)
) -> WeddingPlanRead:
    return plan_read(plan_service.update_plan(db, customer, plan_id, data))


@router.delete("/wedding-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wedding_plan(plan_id: int, customer: User = Depends(require_customer), db: Session = Depends(get_db)) -> None:
    plan_service.delete_plan(db, customer, plan_id)


@router.post("/wedding-plans/{plan_id}/items", response_model=WeddingPlanRead, status_code=status.HTTP_201_CREATED)
def add_plan_item(
    plan_id: int, data: PlanItemCreate, customer: User = Depends(require_customer), db: Session = Depends(get_db)
) -> WeddingPlanRead:
    return plan_read(plan_service.add_item(db, customer, plan_id, data))


@router.patch("/wedding-plans/{plan_id}/items/{item_id}", response_model=WeddingPlanRead)
def update_plan_item(
    plan_id: int,
    item_id: int,
    data: PlanItemUpdate,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> WeddingPlanRead:
    return plan_read(plan_service.update_item(db, customer, plan_id, item_id, data))


@router.delete("/wedding-plans/{plan_id}/items/{item_id}", response_model=WeddingPlanRead)
def delete_plan_item(
    plan_id: int, item_id: int, customer: User = Depends(require_customer), db: Session = Depends(get_db)
) -> WeddingPlanRead:
    return plan_read(plan_service.delete_item(db, customer, plan_id, item_id))

