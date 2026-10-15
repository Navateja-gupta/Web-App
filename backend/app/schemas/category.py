from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import clean_optional_text, clean_required_text


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    icon: str | None = Field(default=None, max_length=255, description="Emoji or image reference")
    display_order: int = Field(default=0, ge=0, le=10000)

    _name = field_validator("name")(clean_required_text)
    _optional = field_validator("description", "icon")(clean_optional_text)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    icon: str | None = Field(default=None, max_length=255)
    display_order: int | None = Field(default=None, ge=0, le=10000)
    is_active: bool | None = None

    _name = field_validator("name")(lambda v: clean_required_text(v) if v is not None else v)
    _optional = field_validator("description", "icon")(clean_optional_text)


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class CategoryRead(CategorySummary):
    description: str | None
    icon: str | None
    display_order: int
    is_active: bool
    # Number of approved, active vendors currently listed (computed, never stored).
    vendor_count: int = 0
    created_at: datetime
