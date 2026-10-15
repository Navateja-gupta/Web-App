from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import BookingStatus
from app.schemas.common import MoneyIn, MoneyOut, clean_optional_text
from app.schemas.parties import CustomerContact, VendorSummary


class BookingCreate(BaseModel):
    vendor_id: int
    package_id: int | None = None
    event_date: date
    event_location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    wedding_plan_id: int | None = None

    _text = field_validator("event_location", "notes")(clean_optional_text)


class BookingConfirm(BaseModel):
    agreed_amount: MoneyIn | None = Field(default=None, description="Required if the booking has no agreed amount yet")


class BookingReason(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)

    _reason = field_validator("reason")(clean_optional_text)


class PackageSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: VendorSummary
    customer: CustomerContact
    package: PackageSummary | None
    quotation_id: int | None
    wedding_plan_id: int | None
    event_date: date
    event_location: str | None
    agreed_amount: MoneyOut | None
    booking_status: BookingStatus
    notes: str | None
    confirmed_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    has_review: bool
    created_at: datetime
