from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError
from app.models.vendor import Vendor, VendorAvailability
from app.schemas.portfolio import AvailabilitySet

MAX_RANGE_DAYS = 366


def resolve_range(start: date | None, end: date | None) -> tuple[date, date]:
    start = start or date.today()
    end = end or start + timedelta(days=90)
    if end < start:
        raise BusinessRuleError("End date must be on or after start date")
    if (end - start).days > MAX_RANGE_DAYS:
        raise BusinessRuleError(f"Date range cannot exceed {MAX_RANGE_DAYS} days")
    return start, end


def list_availability(db: Session, vendor: Vendor, start: date, end: date) -> list[VendorAvailability]:
    return list(
        db.scalars(
            select(VendorAvailability)
            .where(VendorAvailability.vendor_id == vendor.id, VendorAvailability.date.between(start, end))
            .order_by(VendorAvailability.date)
        )
    )


def set_availability(db: Session, vendor: Vendor, day: date, data: AvailabilitySet) -> VendorAvailability:
    """Create or replace the vendor's declared status for one date (one record per date)."""
    if day < date.today():
        raise BusinessRuleError("Availability can only be set for today or future dates")
    entry = db.scalar(
        select(VendorAvailability).where(VendorAvailability.vendor_id == vendor.id, VendorAvailability.date == day)
    )
    if entry is None:
        entry = VendorAvailability(vendor_id=vendor.id, date=day)
        db.add(entry)
    entry.availability_status = data.availability_status
    entry.notes = data.notes
    db.commit()
    return entry


def clear_availability(db: Session, vendor: Vendor, day: date) -> None:
    entry = db.scalar(
        select(VendorAvailability).where(VendorAvailability.vendor_id == vendor.id, VendorAvailability.date == day)
    )
    if entry is not None:
        db.delete(entry)
        db.commit()
