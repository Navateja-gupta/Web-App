from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.dependencies.pagination import PageParams
from app.models.audit import AuditLog
from app.models.booking import Booking, Review
from app.models.category import ServiceCategory
from app.models.enums import (
    ApprovalStatus,
    BookingStatus,
    QuotationRequestStatus,
    ReportStatus,
    UserRole,
)
from app.models.quotation import QuotationRequest
from app.models.report import Report
from app.models.user import User
from app.models.vendor import Vendor


def _counts(db: Session, column, enum_cls) -> dict[str, int]:  # type: ignore[no-untyped-def]
    counts = {member.value: 0 for member in enum_cls}
    for value, count in db.execute(select(column, func.count()).group_by(column)).all():
        counts[value.value] = count
    return counts


def marketplace_stats(db: Session) -> dict[str, object]:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    confirmed_value = db.scalar(
        select(func.coalesce(func.sum(Booking.agreed_amount), 0)).where(
            Booking.booking_status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED])
        )
    ) or Decimal("0")

    per_category = db.execute(
        select(ServiceCategory.name, func.count(Vendor.id))
        .outerjoin(
            Vendor,
            (Vendor.category_id == ServiceCategory.id)
            & (Vendor.approval_status == ApprovalStatus.APPROVED)
            & Vendor.is_active.is_(True),
        )
        .where(ServiceCategory.is_active.is_(True))
        .group_by(ServiceCategory.id, ServiceCategory.name)
        .order_by(ServiceCategory.display_order, ServiceCategory.name)
    ).all()

    return {
        "users_by_role": _counts(db, User.role, UserRole),
        "new_users_last_30_days": db.scalar(select(func.count()).where(User.created_at >= since)) or 0,
        "vendors_by_status": _counts(db, Vendor.approval_status, ApprovalStatus),
        "live_vendors_by_category": [{"category": name, "vendors": count} for name, count in per_category],
        "categories_active": db.scalar(select(func.count()).where(ServiceCategory.is_active.is_(True))) or 0,
        "enquiries_by_status": _counts(db, QuotationRequest.status, QuotationRequestStatus),
        "bookings_by_status": _counts(db, Booking.booking_status, BookingStatus),
        "confirmed_booking_value": float(confirmed_value),
        "reviews_visible": db.scalar(select(func.count()).where(Review.is_visible.is_(True))) or 0,
        "open_reports": db.scalar(select(func.count()).where(Report.status == ReportStatus.OPEN)) or 0,
    }


def list_audit_logs(
    db: Session,
    params: PageParams,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action, autoescape=True))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.options(selectinload(AuditLog.actor))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(params.offset)
        .limit(params.size)
    ).all()
    return list(items), total
