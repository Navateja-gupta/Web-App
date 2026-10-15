import math
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field, PlainSerializer

from app.core.text import collapse_spaces

T = TypeVar("T")

# Money input: exact decimal, non-negative, 2 decimal places.
MoneyIn = Annotated[Decimal, Field(ge=0, le=Decimal("9999999999.99"), max_digits=12, decimal_places=2)]
# Money output: sent to the browser as a JSON number.
MoneyOut = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        return cls(items=items, total=total, page=page, size=size, pages=math.ceil(total / size) if total else 0)


def clean_required_text(value: str) -> str:
    return collapse_spaces(value)


def clean_optional_text(value: str | None) -> str | None:
    """Strip surrounding whitespace; empty strings become None. Inner newlines are kept."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def clean_text_list(max_items: int, max_length: int, label: str):  # type: ignore[no-untyped-def]
    """Build a validator that trims, drops blanks, de-duplicates and bounds a list of short strings."""

    def validator(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            item = collapse_spaces(raw)
            if not item:
                continue
            if len(item) > max_length:
                raise ValueError(f"Each {label} must be at most {max_length} characters")
            if item.lower() not in seen:
                seen.add(item.lower())
                result.append(item)
        if len(result) > max_items:
            raise ValueError(f"At most {max_items} {label}s are allowed")
        return result

    return validator
