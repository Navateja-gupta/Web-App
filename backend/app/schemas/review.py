from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import clean_optional_text
from app.schemas.parties import CustomerContact, VendorSummary


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)

    _comment = field_validator("comment")(clean_optional_text)


class ReviewPublic(BaseModel):
    id: int
    rating: int
    comment: str | None
    # First name + last initial only, to protect customer privacy.
    reviewer_name: str
    created_at: datetime


class VendorReviews(BaseModel):
    average: float | None
    count: int
    items: list[ReviewPublic]
    page: int
    pages: int


class ReviewAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    rating: int
    comment: str | None
    is_visible: bool
    created_at: datetime
    vendor: VendorSummary
    customer: CustomerContact


class ReviewVisibility(BaseModel):
    is_visible: bool
