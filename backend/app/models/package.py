from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint, text, true
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PricingType
from app.models.mixins import Money, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.vendor import Vendor


class VendorPackage(TimestampMixin, Base):
    __tablename__ = "vendor_packages"
    __table_args__ = (
        UniqueConstraint("vendor_id", "name", name="uq_vendor_packages_vendor_id_name"),
        CheckConstraint("price IS NULL OR price >= 0", name="price_non_negative"),
        CheckConstraint("price_max IS NULL OR (price IS NOT NULL AND price_max >= price)", name="price_range_valid"),
        # Only "quote on request" packages may omit a price.
        CheckConstraint("pricing_type = 'quote_on_request' OR price IS NOT NULL", name="price_required"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    pricing_type: Mapped[PricingType] = enum_column(PricingType, "pricing_type")
    price: Mapped[Decimal | None] = mapped_column(Money)
    # Optional upper bound for a price range (e.g. 40,000 – 60,000).
    price_max: Mapped[Decimal | None] = mapped_column(Money)
    inclusions: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list, server_default=text("'{}'"))
    exclusions: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list, server_default=text("'{}'"))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    vendor: Mapped[Vendor] = relationship(back_populates="packages")
