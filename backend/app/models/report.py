from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ReportReason, ReportStatus
from app.models.mixins import TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.booking import Review
    from app.models.user import User
    from app.models.vendor import Vendor


class Report(TimestampMixin, Base):
    """A complaint about a vendor listing or a review, handled by administrators."""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("vendor_id IS NOT NULL OR review_id IS NOT NULL", name="has_target"),
        Index("ix_reports_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    reason: Mapped[ReportReason] = enum_column(ReportReason, "report_reason")
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus] = enum_column(
        ReportStatus, "report_status", default=ReportStatus.OPEN, server_default=ReportStatus.OPEN.value
    )
    admin_notes: Mapped[str | None] = mapped_column(Text)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reporter: Mapped[User | None] = relationship(foreign_keys=[reporter_id])
    vendor: Mapped[Vendor | None] = relationship()
    review: Mapped[Review | None] = relationship()
