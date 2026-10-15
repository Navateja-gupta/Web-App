from sqlalchemy import String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ServiceCategory(TimestampMixin, Base):
    """Created and managed by administrators at runtime; never hardcoded."""

    __tablename__ = "service_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(90), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(default=0, server_default="0")
    # Deactivate instead of deleting so historical vendors/bookings stay intact.
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
