from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PlanItemStatus
from app.models.mixins import Money, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.category import ServiceCategory
    from app.models.vendor import Vendor


class WeddingPlan(TimestampMixin, Base):
    """One wedding-related event (e.g. engagement, haldi, wedding, reception)."""

    __tablename__ = "wedding_plans"
    __table_args__ = (
        CheckConstraint("estimated_budget IS NULL OR estimated_budget >= 0", name="budget_non_negative"),
        CheckConstraint("guest_count IS NULL OR guest_count > 0", name="guest_count_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_name: Mapped[str] = mapped_column(String(150))
    event_date: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(255))
    estimated_budget: Mapped[Decimal | None] = mapped_column(Money)
    guest_count: Mapped[int | None]

    items: Mapped[list[WeddingPlanItem]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="WeddingPlanItem.id"
    )


class WeddingPlanItem(TimestampMixin, Base):
    """A budget line. vendor/package are optional so expenses can be tracked before choosing a vendor."""

    __tablename__ = "wedding_plan_items"
    __table_args__ = (
        CheckConstraint("estimated_cost >= 0", name="estimated_cost_non_negative"),
        CheckConstraint("actual_cost IS NULL OR actual_cost >= 0", name="actual_cost_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    wedding_plan_id: Mapped[int] = mapped_column(ForeignKey("wedding_plans.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("service_categories.id", ondelete="SET NULL"))
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"))
    package_id: Mapped[int | None] = mapped_column(ForeignKey("vendor_packages.id", ondelete="SET NULL"))
    description: Mapped[str] = mapped_column(String(255))
    estimated_cost: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), server_default="0")
    actual_cost: Mapped[Decimal | None] = mapped_column(Money)
    status: Mapped[PlanItemStatus] = enum_column(
        PlanItemStatus, "plan_item_status", default=PlanItemStatus.PLANNED, server_default=PlanItemStatus.PLANNED.value
    )

    plan: Mapped[WeddingPlan] = relationship(back_populates="items")
    category: Mapped[ServiceCategory | None] = relationship()
    vendor: Mapped[Vendor | None] = relationship()
