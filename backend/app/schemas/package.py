from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import PricingType
from app.schemas.common import MoneyIn, MoneyOut, clean_optional_text, clean_required_text, clean_text_list

_clean_items = clean_text_list(max_items=30, max_length=255, label="item")


class PackageCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=3000)
    pricing_type: PricingType
    price: MoneyIn | None = Field(default=None, description="Required unless pricing_type is quote_on_request")
    price_max: MoneyIn | None = Field(default=None, description="Optional upper end of a price range")
    inclusions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)

    _name = field_validator("name")(clean_required_text)
    _description = field_validator("description")(clean_optional_text)
    _items = field_validator("inclusions", "exclusions")(_clean_items)


class PackageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=3000)
    pricing_type: PricingType | None = None
    price: MoneyIn | None = None
    price_max: MoneyIn | None = None
    inclusions: list[str] | None = None
    exclusions: list[str] | None = None
    is_active: bool | None = None

    _name = field_validator("name")(lambda v: clean_required_text(v) if v is not None else v)
    _description = field_validator("description")(clean_optional_text)
    _items = field_validator("inclusions", "exclusions")(lambda v: _clean_items(v) if v is not None else v)


class PackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    name: str
    description: str | None
    pricing_type: PricingType
    price: MoneyOut | None
    price_max: MoneyOut | None
    inclusions: list[str]
    exclusions: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
