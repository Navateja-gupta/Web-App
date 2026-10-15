from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, SmallInteger, String, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import BookingStatus
from app.models.mixins import Money, TimestampMixin, enum_column


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("agreed_amount IS NULL OR agreed_amount >= 0", name="agreed_amount_non_negative"),
        Index("ix_bookings_vendor_id_event_date", "vendor_id", "event_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"))
    package_id: Mapped[int | None] = mapped_column(ForeignKey("vendor_packages.id", ondelete="SET NULL"))
    # A quotation can lead to at most one booking.
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id", ondelete="SET NULL"), unique=True)
    wedding_plan_id: Mapped[int | None] = mapped_column(ForeignKey("wedding_plans.id", ondelete="SET NULL"))
    event_date: Mapped[date] = mapped_column(Date)
    event_location: Mapped[str | None] = mapped_column(String(255))
    agreed_amount: Mapped[Decimal | None] = mapped_column(Money)
    booking_status: Mapped[BookingStatus] = enum_column(
        BookingStatus,
        "booking_status",
        default=BookingStatus.REQUESTED,
        server_default=BookingStatus.REQUESTED.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)


class Review(Base):
    """Only allowed for completed bookings; one review per booking."""

    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"), index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"), unique=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    comment: Mapped[str | None] = mapped_column(Text)
    # Lets an admin hide a review after a valid complaint without deleting it.
    is_visible: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
