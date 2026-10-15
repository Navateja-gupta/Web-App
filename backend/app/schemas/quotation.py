from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import QuotationRequestStatus, QuotationStatus
from app.schemas.common import MoneyIn, MoneyOut, clean_optional_text, clean_required_text, clean_text_list
from app.schemas.parties import CustomerContact, VendorSummary

_clean_items = clean_text_list(max_items=30, max_length=255, label="item")


class QuotationRequestCreate(BaseModel):
    vendor_ids: list[int] = Field(min_length=1, max_length=10, description="Send the same enquiry to up to 10 vendors")
    service_date: date
    event_location: str = Field(min_length=2, max_length=255)
    guest_count: int | None = Field(default=None, ge=1, le=100000)
    requirements: str = Field(min_length=10, max_length=5000)
    budget: MoneyIn | None = None
    wedding_plan_id: int | None = None

    _location = field_validator("event_location")(clean_required_text)

    @field_validator("requirements")
    @classmethod
    def strip_requirements(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Describe your requirements in at least 10 characters")
        return value

    @field_validator("vendor_ids")
    @classmethod
    def unique_vendors(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class DeclineRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)

    _reason = field_validator("reason")(clean_optional_text)


class QuotationCreate(BaseModel):
    quoted_amount: MoneyIn
    description: str | None = Field(default=None, max_length=3000)
    inclusions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    validity_date: date | None = Field(default=None, description="Last date the customer can accept")

    _description = field_validator("description")(clean_optional_text)
    _items = field_validator("inclusions", "exclusions")(_clean_items)


class QuotationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_request_id: int
    vendor: VendorSummary
    quoted_amount: MoneyOut
    description: str | None
    inclusions: list[str]
    exclusions: list[str]
    validity_date: date | None
    status: QuotationStatus
    created_at: datetime


class QuotationRequestRead(BaseModel):
    """Customer's view of their own enquiry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: VendorSummary
    service_date: date
    event_location: str
    guest_count: int | None
    requirements: str
    budget: MoneyOut | None
    status: QuotationRequestStatus
    vendor_response: str | None
    wedding_plan_id: int | None
    created_at: datetime
    updated_at: datetime
    quotations: list[QuotationRead]


class EnquiryRead(QuotationRequestRead):
    """Vendor/admin view: includes the customer's contact details."""

    customer: CustomerContact
