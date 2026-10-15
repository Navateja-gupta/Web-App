from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.booking import Booking
from app.models.enums import PricingType
from app.models.package import VendorPackage
from app.models.user import User
from app.models.vendor import Vendor
from app.models.wedding_plan import WeddingPlanItem
from app.schemas.package import PackageCreate, PackageUpdate
from app.services.audit import record_audit

MAX_PACKAGES_PER_VENDOR = 20


def list_packages(db: Session, vendor: Vendor, *, include_inactive: bool) -> list[VendorPackage]:
    stmt = select(VendorPackage).where(VendorPackage.vendor_id == vendor.id)
    if not include_inactive:
        stmt = stmt.where(VendorPackage.is_active.is_(True))
    return list(db.scalars(stmt.order_by(VendorPackage.price.asc().nulls_last(), VendorPackage.id)))


def get_package(db: Session, vendor: Vendor, package_id: int) -> VendorPackage:
    """Scoped to the vendor, so nobody can reach another vendor's package by guessing an id."""
    package = db.scalar(
        select(VendorPackage).where(VendorPackage.id == package_id, VendorPackage.vendor_id == vendor.id)
    )
    if package is None:
        raise NotFoundError("Package not found")
    return package


def _normalize_pricing(package: VendorPackage) -> None:
    if package.pricing_type == PricingType.QUOTE_ON_REQUEST:
        package.price = None
        package.price_max = None
        return
    if package.price is None:
        raise BusinessRuleError("Enter a price, or choose 'Quote on request'")
    if package.price_max is not None and package.price_max < package.price:
        raise BusinessRuleError("The maximum price must be greater than or equal to the price")


def _ensure_unique_name(db: Session, vendor: Vendor, name: str, exclude_id: int | None = None) -> None:
    stmt = select(VendorPackage.id).where(
        VendorPackage.vendor_id == vendor.id, func.lower(VendorPackage.name) == name.lower()
    )
    if exclude_id is not None:
        stmt = stmt.where(VendorPackage.id != exclude_id)
    if db.scalar(stmt):
        raise ConflictError("You already have a package with this name")


def create_package(db: Session, vendor: Vendor, data: PackageCreate, actor: User) -> VendorPackage:
    count = db.scalar(select(func.count()).where(VendorPackage.vendor_id == vendor.id)) or 0
    if count >= MAX_PACKAGES_PER_VENDOR:
        raise BusinessRuleError(f"A vendor can have at most {MAX_PACKAGES_PER_VENDOR} packages")
    _ensure_unique_name(db, vendor, data.name)

    package = VendorPackage(vendor_id=vendor.id, **data.model_dump())
    _normalize_pricing(package)
    db.add(package)
    db.flush()
    record_audit(db, actor_id=actor.id, action="package.created", entity_type="package", entity_id=package.id,
                 details={"vendor_id": vendor.id})
    db.commit()
    return package


def update_package(db: Session, vendor: Vendor, package_id: int, data: PackageUpdate, actor: User) -> VendorPackage:
    package = get_package(db, vendor, package_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("name", "pricing_type", "is_active", "inclusions", "exclusions"):
        if field in changes and changes[field] is None:
            changes.pop(field)
    if "name" in changes and changes["name"].lower() != package.name.lower():
        _ensure_unique_name(db, vendor, changes["name"], exclude_id=package.id)

    for field, value in changes.items():
        setattr(package, field, value)
    _normalize_pricing(package)

    record_audit(db, actor_id=actor.id, action="package.updated", entity_type="package", entity_id=package.id,
                 details={"vendor_id": vendor.id, "fields": sorted(changes)})
    db.commit()
    db.refresh(package)
    return package


def delete_package(db: Session, vendor: Vendor, package_id: int, actor: User) -> None:
    package = get_package(db, vendor, package_id)
    in_use = db.scalar(select(Booking.id).where(Booking.package_id == package.id).limit(1)) or db.scalar(
        select(WeddingPlanItem.id).where(WeddingPlanItem.package_id == package.id).limit(1)
    )
    if in_use:
        raise ConflictError("This package is used by bookings or wedding plans. Deactivate it instead.")
    record_audit(db, actor_id=actor.id, action="package.deleted", entity_type="package", entity_id=package.id,
                 details={"vendor_id": vendor.id, "name": package.name})
    db.delete(package)
    db.commit()
