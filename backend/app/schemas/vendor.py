from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import ApprovalStatus
from app.schemas.category import CategorySummary
from app.schemas.common import MoneyIn, MoneyOut, clean_optional_text, clean_required_text, clean_text_list
from app.schemas.user import normalize_phone

_clean_areas = clean_text_list(max_items=30, max_length=100, label="service area")


def _required_phone(value: str) -> str:
    phone = normalize_phone(value)
    if phone is None:
        raise ValueError("Enter a contact phone number")
    return phone


def _lower_email(value: str | None) -> str | None:
    return value.lower() if value else None


class VendorCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=150)
    category_id: int
    description: str | None = Field(default=None, max_length=5000)
    contact_phone: str
    contact_email: EmailStr | None = None
    location: str = Field(min_length=2, max_length=120, description="Town/city, e.g. Kamareddy")
    service_areas: list[str] = Field(default_factory=list, description="Towns/areas served")
    starting_price: MoneyIn | None = Field(default=None, description="Leave empty to show 'Contact for pricing'")

    _text = field_validator("business_name", "location")(clean_required_text)
    _description = field_validator("description")(clean_optional_text)
    _phone = field_validator("contact_phone")(_required_phone)
    _email = field_validator("contact_email")(_lower_email)
    _areas = field_validator("service_areas")(_clean_areas)


class VendorUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=150)
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=5000)
    contact_phone: str | None = None
    contact_email: EmailStr | None = None
    location: str | None = Field(default=None, min_length=2, max_length=120)
    service_areas: list[str] | None = None
    starting_price: MoneyIn | None = None

    _text = field_validator("business_name", "location")(lambda v: clean_required_text(v) if v is not None else v)
    _description = field_validator("description")(clean_optional_text)
    _phone = field_validator("contact_phone")(lambda v: _required_phone(v) if v is not None else v)
    _email = field_validator("contact_email")(_lower_email)
    _areas = field_validator("service_areas")(lambda v: _clean_areas(v) if v is not None else v)


class AdminVendorUpdate(VendorUpdate):
    is_active: bool | None = None


class ApprovalDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class VerificationUpdate(BaseModel):
    is_verified: bool
    notes: str | None = Field(default=None, max_length=2000)


class ClaimCodeRead(BaseModel):
    code: str
    expires_at: datetime


class ClaimRequest(BaseModel):
    code: str = Field(min_length=4, max_length=20)


class VendorPublic(BaseModel):
    """Safe for anyone to see."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    business_name: str
    category: CategorySummary
    description: str | None
    contact_phone: str
    contact_email: str | None
    location: str
    service_areas: list[str]
    starting_price: MoneyOut | None
    is_verified: bool
    cover_image_url: str | None = None
    # Computed only from real, visible reviews of completed bookings.
    rating_average: float | None = None
    review_count: int = 0


class VendorOwnerRead(VendorPublic):
    """What the vendor sees about their own profile."""

    approval_status: ApprovalStatus
    is_active: bool
    status_reason: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OwnerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class VendorAdminRead(VendorOwnerRead):
    """Administrator view, including internal notes."""

    user: OwnerSummary | None
    verified_at: datetime | None
    verification_notes: str | None
    created_by_id: int | None
    has_pending_claim_code: bool = False
