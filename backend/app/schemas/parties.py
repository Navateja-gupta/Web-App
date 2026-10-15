"""Small summaries of the people/businesses on either side of an enquiry or booking."""

from pydantic import BaseModel, ConfigDict

from app.schemas.category import CategorySummary


class VendorSummary(BaseModel):
    """Public business details (already shown on the vendor's public profile)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    business_name: str
    category: CategorySummary
    contact_phone: str
    location: str


class VendorBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    business_name: str


class CustomerContact(BaseModel):
    """Only returned to the customer themselves, the vendor they contacted, or administrators."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None
