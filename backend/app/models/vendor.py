from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ApprovalStatus, AvailabilityStatus, MediaType
from app.models.mixins import Money, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.category import ServiceCategory
    from app.models.package import VendorPackage
    from app.models.user import User


class Vendor(TimestampMixin, Base):
    __tablename__ = "vendors"
    __table_args__ = (
        CheckConstraint("starting_price IS NULL OR starting_price >= 0", name="starting_price_non_negative"),
        # Same business name cannot be listed twice in one category (case-insensitive).
        Index(
            "uq_vendors_category_id_business_name_lower",
            "category_id",
            text("lower(business_name)"),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable: an admin may create the profile before the vendor has an account.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("service_categories.id", ondelete="RESTRICT"), index=True)

    business_name: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(170), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    contact_phone: Mapped[str] = mapped_column(String(20))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(120), index=True)
    service_areas: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), default=list, server_default=text("'{}'")
    )
    starting_price: Mapped[Decimal | None] = mapped_column(Money)

    # Approval (admin decision) is deliberately separate from is_active (on/off switch).
    approval_status: Mapped[ApprovalStatus] = enum_column(
        ApprovalStatus,
        "approval_status",
        default=ApprovalStatus.PENDING,
        server_default=ApprovalStatus.PENDING.value,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    # Reason shown to the vendor when rejected or suspended.
    status_reason: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    # One-time code that lets a vendor link an admin-created profile to their account.
    # Only the SHA-256 hash is stored.
    claim_code_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    claim_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Verification = admin has checked identity/business documents. Never fabricated.
    is_verified: Mapped[bool] = mapped_column(default=False, server_default=false())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User | None] = relationship(foreign_keys=[user_id])
    category: Mapped[ServiceCategory] = relationship()
    packages: Mapped[list[VendorPackage]] = relationship(back_populates="vendor", order_by="VendorPackage.id")
    portfolio_items: Mapped[list[VendorPortfolio]] = relationship(
        back_populates="vendor", order_by="VendorPortfolio.display_order"
    )


class VendorPortfolio(Base):
    __tablename__ = "vendor_portfolio"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    media_path: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[MediaType] = enum_column(MediaType, "media_type", default=MediaType.IMAGE)
    caption: Mapped[str | None] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vendor: Mapped[Vendor] = relationship(back_populates="portfolio_items")


class VendorAvailability(TimestampMixin, Base):
    """Vendor-declared availability. Not a guarantee until confirmed via a booking."""

    __tablename__ = "vendor_availability"
    __table_args__ = (UniqueConstraint("vendor_id", "date", name="uq_vendor_availability_vendor_id_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    # `date_type` alias: the column is named `date`, which would shadow the type name.
    date: Mapped[date_type] = mapped_column(Date)
    availability_status: Mapped[AvailabilityStatus] = enum_column(AvailabilityStatus, "availability_status")
    notes: Mapped[str | None] = mapped_column(String(255))
