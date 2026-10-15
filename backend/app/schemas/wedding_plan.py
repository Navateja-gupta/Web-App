from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import PlanItemStatus
from app.schemas.category import CategorySummary
from app.schemas.common import MoneyIn, MoneyOut, clean_optional_text, clean_required_text
from app.schemas.parties import VendorBrief


class WeddingPlanCreate(BaseModel):
    event_name: str = Field(min_length=2, max_length=150, description="e.g. Wedding, Engagement, Haldi, Reception")
    event_date: date | None = None
    location: str | None = Field(default=None, max_length=255)
    estimated_budget: MoneyIn | None = None
    guest_count: int | None = Field(default=None, ge=1, le=100000)

    _name = field_validator("event_name")(clean_required_text)
    _location = field_validator("location")(clean_optional_text)


class WeddingPlanUpdate(BaseModel):
    event_name: str | None = Field(default=None, min_length=2, max_length=150)
    event_date: date | None = None
    location: str | None = Field(default=None, max_length=255)
    estimated_budget: MoneyIn | None = None
    guest_count: int | None = Field(default=None, ge=1, le=100000)

    _name = field_validator("event_name")(lambda v: clean_required_text(v) if v is not None else v)
    _location = field_validator("location")(clean_optional_text)


class PlanItemCreate(BaseModel):
    description: str = Field(min_length=2, max_length=255)
    category_id: int | None = None
    vendor_id: int | None = None
    package_id: int | None = None
    estimated_cost: MoneyIn = Field(default=0)
    actual_cost: MoneyIn | None = None
    status: PlanItemStatus = PlanItemStatus.PLANNED

    _description = field_validator("description")(clean_required_text)


class PlanItemUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=2, max_length=255)
    category_id: int | None = None
    vendor_id: int | None = None
    package_id: int | None = None
    estimated_cost: MoneyIn | None = None
    actual_cost: MoneyIn | None = None
    status: PlanItemStatus | None = None

    _description = field_validator("description")(lambda v: clean_required_text(v) if v is not None else v)


class PlanItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    category: CategorySummary | None
    vendor: VendorBrief | None
    package_id: int | None
    estimated_cost: MoneyOut
    actual_cost: MoneyOut | None
    status: PlanItemStatus
    created_at: datetime


class BudgetSummary(BaseModel):
    estimated_budget: MoneyOut | None
    total_estimated: MoneyOut
    total_actual: MoneyOut
    # Actual cost where known, otherwise the estimate (cancelled items excluded).
    committed: MoneyOut
    remaining: MoneyOut | None
    over_budget: bool
    item_count: int
    by_status: dict[str, int]


class WeddingPlanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_name: str
    event_date: date | None
    location: str | None
    estimated_budget: MoneyOut | None
    guest_count: int | None
    created_at: datetime
    updated_at: datetime
    budget: BudgetSummary


class WeddingPlanRead(WeddingPlanSummary):
    items: list[PlanItemRead]
