import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

# Money: up to 9,999,999,999.99 with exact decimal arithmetic.
Money = Numeric(12, 2)


def enum_column(enum_cls: type[enum.Enum], name: str, **kwargs: Any) -> Any:
    """Store an enum as VARCHAR + CHECK constraint (easier to evolve than a native PG enum)."""
    return mapped_column(
        Enum(
            enum_cls,
            name=name,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            length=30,
            values_callable=lambda members: [member.value for member in members],
        ),
        **kwargs,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
