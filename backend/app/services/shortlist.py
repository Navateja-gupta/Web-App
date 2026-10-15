from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.shortlist import CustomerShortlist
from app.models.user import User
from app.models.vendor import Vendor
from app.services.vendors import PUBLIC_CONDITIONS, get_public_vendor_by_id


def list_shortlist(db: Session, customer: User) -> list[tuple[Vendor, datetime]]:
    """Shortlisted vendors that are still publicly listed (suspended/hidden ones are left out)."""
    rows = db.execute(
        select(Vendor, CustomerShortlist.created_at)
        .join(CustomerShortlist, CustomerShortlist.vendor_id == Vendor.id)
        .join(Vendor.category)
        .where(CustomerShortlist.customer_id == customer.id, *PUBLIC_CONDITIONS)
        .options(selectinload(Vendor.category), selectinload(Vendor.portfolio_items))
        .order_by(CustomerShortlist.created_at.desc(), CustomerShortlist.id.desc())
    ).all()
    return [(vendor, added_at) for vendor, added_at in rows]


def shortlisted_ids(db: Session, customer: User) -> list[int]:
    return [vendor.id for vendor, _ in list_shortlist(db, customer)]


def add_to_shortlist(db: Session, customer: User, vendor_id: int) -> tuple[Vendor, datetime]:
    """Idempotent: adding the same vendor twice keeps a single entry."""
    vendor = get_public_vendor_by_id(db, vendor_id)
    entry = db.scalar(
        select(CustomerShortlist).where(
            CustomerShortlist.customer_id == customer.id, CustomerShortlist.vendor_id == vendor.id
        )
    )
    if entry is None:
        entry = CustomerShortlist(customer_id=customer.id, vendor_id=vendor.id)
        db.add(entry)
        try:
            db.commit()
        except IntegrityError:
            # Same vendor added concurrently (e.g. double click); the unique constraint kept one row.
            db.rollback()
            entry = db.scalar(
                select(CustomerShortlist).where(
                    CustomerShortlist.customer_id == customer.id, CustomerShortlist.vendor_id == vendor.id
                )
            )
        db.refresh(entry)
    return vendor, entry.created_at


def remove_from_shortlist(db: Session, customer: User, vendor_id: int) -> None:
    db.execute(
        delete(CustomerShortlist).where(
            CustomerShortlist.customer_id == customer.id, CustomerShortlist.vendor_id == vendor_id
        )
    )
    db.commit()
