"""Administrator operations: statistics, enquiries, bookings, reviews, reports and audit logs."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.dependencies.pagination import PageParams, get_page_params
from app.models.enums import BookingStatus, QuotationRequestStatus, ReportStatus
from app.models.user import User
from app.schemas.booking import BookingRead, BookingReason
from app.schemas.common import Page
from app.schemas.quotation import EnquiryRead
from app.schemas.report import AuditLogRead, ReportRead, ReportResolve
from app.schemas.review import ReviewAdminRead, ReviewVisibility
from app.services import admin_stats
from app.services import bookings as booking_service
from app.services import quotations as quotation_service
from app.services import reports as report_service
from app.services import reviews as review_service

router = APIRouter(prefix="/admin", tags=["admin: operations"])


@router.get("/stats")
def stats(_admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict[str, Any]:
    """Marketplace overview figures, all computed live from the database."""
    return admin_stats.marketplace_stats(db)


@router.get("/quotation-requests", response_model=Page[EnquiryRead])
def list_enquiries(
    status_filter: QuotationRequestStatus | None = Query(default=None, alias="status"),
    vendor_id: int | None = None,
    params: PageParams = Depends(get_page_params),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[EnquiryRead]:
    items, total = quotation_service.list_all_enquiries(db, params, status_filter, vendor_id)
    return Page[EnquiryRead].build([EnquiryRead.model_validate(i) for i in items], total, params.page, params.size)


@router.get("/bookings", response_model=Page[BookingRead])
def list_bookings(
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    vendor_id: int | None = None,
    params: PageParams = Depends(get_page_params),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[BookingRead]:
    items, total = booking_service.list_bookings(db, params, status=status_filter, vendor_id=vendor_id)
    return Page[BookingRead].build([BookingRead.model_validate(b) for b in items], total, params.page, params.size)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingRead)
def cancel_booking(
    booking_id: int, data: BookingReason, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):  # type: ignore[no-untyped-def]
    booking = booking_service.get_booking(db, booking_id)
    return booking_service.change_status(db, booking, "cancel", admin, reason=data.reason)


@router.post("/bookings/{booking_id}/complete", response_model=BookingRead)
def complete_booking(booking_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    booking = booking_service.get_booking(db, booking_id)
    return booking_service.change_status(db, booking, "complete", admin)


@router.get("/reviews", response_model=Page[ReviewAdminRead])
def list_reviews(
    vendor_id: int | None = None,
    is_visible: bool | None = None,
    params: PageParams = Depends(get_page_params),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[ReviewAdminRead]:
    items, total = review_service.list_admin_reviews(db, params, vendor_id=vendor_id, is_visible=is_visible)
    return Page[ReviewAdminRead].build([ReviewAdminRead.model_validate(r) for r in items], total, params.page, params.size)


@router.patch("/reviews/{review_id}", response_model=ReviewAdminRead)
def set_review_visibility(
    review_id: int, data: ReviewVisibility, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):  # type: ignore[no-untyped-def]
    """Hide a review after a valid complaint (it is kept, not deleted)."""
    return review_service.set_visibility(db, admin, review_id, data.is_visible)


@router.get("/reports", response_model=Page[ReportRead])
def list_reports(
    status_filter: ReportStatus | None = Query(default=None, alias="status"),
    params: PageParams = Depends(get_page_params),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[ReportRead]:
    items, total = report_service.list_reports(db, params, status_filter)
    return Page[ReportRead].build([ReportRead.model_validate(r) for r in items], total, params.page, params.size)


@router.post("/reports/{report_id}/resolve", response_model=ReportRead)
def resolve_report(
    report_id: int, data: ReportResolve, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):  # type: ignore[no-untyped-def]
    return report_service.resolve_report(db, admin, report_id, data)


@router.get("/audit-logs", response_model=Page[AuditLogRead])
def list_audit_logs(
    action: str | None = Query(default=None, max_length=80, description="Prefix, e.g. 'vendor.' or 'booking.confirmed'"),
    entity_type: str | None = Query(default=None, max_length=50),
    entity_id: int | None = None,
    params: PageParams = Depends(get_page_params),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[AuditLogRead]:
    items, total = admin_stats.list_audit_logs(db, params, action=action, entity_type=entity_type, entity_id=entity_id)
    return Page[AuditLogRead].build([AuditLogRead.model_validate(a) for a in items], total, params.page, params.size)
