from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AvailabilityStatus, MediaType
from app.schemas.common import clean_optional_text


class PortfolioRead(BaseModel):
    id: int
    url: str
    media_type: MediaType
    caption: str | None
    display_order: int
    created_at: datetime


class PortfolioUpdate(BaseModel):
    caption: str | None = Field(default=None, max_length=255)
    display_order: int | None = Field(default=None, ge=0, le=1000)

    _caption = field_validator("caption")(clean_optional_text)


class AvailabilitySet(BaseModel):
    availability_status: AvailabilityStatus
    notes: str | None = Field(default=None, max_length=255)

    _notes = field_validator("notes")(clean_optional_text)


class AvailabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    availability_status: AvailabilityStatus
    notes: str | None
