from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import QuotationRequestStatus, QuotationStatus
from app.models.mixins import Money, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vendor import Vendor


class QuotationRequest(TimestampMixin, Base):
    """A customer's enquiry to one vendor."""

    __tablename__ = "quotation_requests"
    __table_args__ = (
        CheckConstraint("guest_count IS NULL OR guest_count > 0", name="guest_count_positive"),
        CheckConstraint("budget IS NULL OR budget >= 0", name="budget_non_negative"),
        Index("ix_quotation_requests_vendor_id_status", "vendor_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"))
    wedding_plan_id: Mapped[int | None] = mapped_column(ForeignKey("wedding_plans.id", ondelete="SET NULL"))
    service_date: Mapped[date] = mapped_column(Date)
    event_location: Mapped[str] = mapped_column(String(255))
    guest_count: Mapped[int | None]
    requirements: Mapped[str] = mapped_column(Text)
    budget: Mapped[Decimal | None] = mapped_column(Money)
    status: Mapped[QuotationRequestStatus] = enum_column(
        QuotationRequestStatus,
        "quotation_request_status",
        default=QuotationRequestStatus.PENDING,
        server_default=QuotationRequestStatus.PENDING.value,
    )
    # Vendor's message when declining (shown to the customer).
    vendor_response: Mapped[str | None] = mapped_column(Text)

    quotations: Mapped[list[Quotation]] = relationship(back_populates="request", order_by="Quotation.id")
    vendor: Mapped[Vendor] = relationship()
    customer: Mapped[User] = relationship()


class Quotation(TimestampMixin, Base):
    """A vendor's priced response. Never becomes a booking without explicit acceptance."""

    __tablename__ = "quotations"
    __table_args__ = (CheckConstraint("quoted_amount >= 0", name="quoted_amount_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_request_id: Mapped[int] = mapped_column(
        ForeignKey("quotation_requests.id", ondelete="RESTRICT"), index=True
    )
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"), index=True)
    quoted_amount: Mapped[Decimal] = mapped_column(Money)
    description: Mapped[str | None] = mapped_column(Text)
    inclusions: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list, server_default=text("'{}'"))
    exclusions: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list, server_default=text("'{}'"))
    validity_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[QuotationStatus] = enum_column(
        QuotationStatus, "quotation_status", default=QuotationStatus.SENT, server_default=QuotationStatus.SENT.value
    )

    request: Mapped[QuotationRequest] = relationship(back_populates="quotations")
    vendor: Mapped[Vendor] = relationship()
