from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.dependencies.pagination import PageParams
from app.models.booking import Review
from app.models.enums import ReportStatus
from app.models.report import Report
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.report import ReportCreate, ReportResolve
from app.services import notify_events
from app.services.audit import record_audit
from app.services.vendors import get_public_vendor_by_id


def create_report(db: Session, reporter: User, data: ReportCreate) -> Report:
    if data.vendor_id is not None:
        get_public_vendor_by_id(db, data.vendor_id)
    else:
        review = db.get(Review, data.review_id)
        if review is None or not review.is_visible:
            raise NotFoundError("Review not found")

    duplicate = db.scalar(
        select(Report.id).where(
            Report.reporter_id == reporter.id,
            Report.vendor_id.is_(data.vendor_id) if data.vendor_id is None else Report.vendor_id == data.vendor_id,
            Report.review_id.is_(data.review_id) if data.review_id is None else Report.review_id == data.review_id,
            Report.status == ReportStatus.OPEN,
        )
    )
    if duplicate:
        raise ConflictError("You have already reported this. Our team will review it.")

    report = Report(reporter_id=reporter.id, **data.model_dump())
    db.add(report)
    db.flush()
    record_audit(db, actor_id=reporter.id, action="report.created", entity_type="report", entity_id=report.id)
    notify_events.report_created(db, "a vendor listing" if data.vendor_id is not None else "a review")
    db.commit()
    return report


def _query():  # type: ignore[no-untyped-def]
    return select(Report).options(
        selectinload(Report.reporter), selectinload(Report.vendor).selectinload(Vendor.category)
    ).execution_options(populate_existing=True)


def list_reports(db: Session, params: PageParams, status: ReportStatus | None = None) -> tuple[list[Report], int]:
    stmt = _query()
    if status is not None:
        stmt = stmt.where(Report.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.order_by(Report.created_at.desc(), Report.id.desc()).offset(params.offset).limit(params.size)).all()
    return list(items), total


def resolve_report(db: Session, admin: User, report_id: int, data: ReportResolve) -> Report:
    report = db.scalar(_query().where(Report.id == report_id))
    if report is None:
        raise NotFoundError("Report not found")
    if report.status != ReportStatus.OPEN:
        raise BusinessRuleError("This report has already been handled")
    report.status = ReportStatus(data.status)
    report.admin_notes = data.admin_notes
    report.resolved_by_id = admin.id
    report.resolved_at = datetime.now(timezone.utc)
    record_audit(db, actor_id=admin.id, action=f"report.{data.status}", entity_type="report", entity_id=report.id)
    db.commit()
    return db.scalar(_query().where(Report.id == report.id))  # type: ignore[return-value]
