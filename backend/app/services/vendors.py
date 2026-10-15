import re
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import Select, func, or_, select, union
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.security import hash_token
from app.core.text import unique_slug
from app.dependencies.pagination import PageParams
from app.models.category import ServiceCategory
from app.models.enums import ApprovalStatus, AvailabilityStatus, UserRole
from app.models.package import VendorPackage
from app.models.user import User
from app.models.vendor import Vendor, VendorAvailability
from app.schemas.vendor import AdminVendorUpdate, VendorCreate, VendorUpdate
from app.services.audit import record_audit

VendorSort = Literal["newest", "price_low", "price_high", "name"]

# The single definition of "publicly visible".
PUBLIC_CONDITIONS = (
    Vendor.approval_status == ApprovalStatus.APPROVED,
    Vendor.is_active.is_(True),
    ServiceCategory.is_active.is_(True),
)

# action -> (allowed current statuses, resulting status, audit action)
APPROVAL_TRANSITIONS: dict[str, tuple[set[ApprovalStatus], ApprovalStatus, str]] = {
    "approve": (
        {ApprovalStatus.PENDING, ApprovalStatus.REJECTED, ApprovalStatus.SUSPENDED},
        ApprovalStatus.APPROVED,
        "vendor.approved",
    ),
    "reject": ({ApprovalStatus.PENDING}, ApprovalStatus.REJECTED, "vendor.rejected"),
    "suspend": ({ApprovalStatus.APPROVED}, ApprovalStatus.SUSPENDED, "vendor.suspended"),
}

REQUIRED_FIELDS = ("business_name", "category_id", "contact_phone", "location")
CLAIM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I to avoid misreading


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _with_relations(stmt: Select) -> Select:  # type: ignore[type-arg]
    # populate_existing: re-read rows even if already in the session, so relationships
    # (e.g. category after a category change, newly added photos) are never stale.
    return stmt.options(
        selectinload(Vendor.category), selectinload(Vendor.portfolio_items), selectinload(Vendor.user)
    ).execution_options(populate_existing=True)


# ---------- Lookups ----------

def get_vendor(db: Session, vendor_id: int) -> Vendor:
    vendor = db.scalar(_with_relations(select(Vendor).where(Vendor.id == vendor_id)))
    if vendor is None:
        raise NotFoundError("Vendor not found")
    return vendor


def get_vendor_for_user(db: Session, user: User) -> Vendor | None:
    return db.scalar(_with_relations(select(Vendor).where(Vendor.user_id == user.id)))


def get_public_vendor_by_id(db: Session, vendor_id: int) -> Vendor:
    vendor = db.scalar(
        _with_relations(select(Vendor).join(Vendor.category).where(Vendor.id == vendor_id, *PUBLIC_CONDITIONS))
    )
    if vendor is None:
        raise NotFoundError("Vendor not found")
    return vendor


def public_locations(db: Session) -> list[str]:
    """Towns and service areas of currently listed vendors (for the location filter)."""
    towns = select(Vendor.location.label("name")).join(Vendor.category).where(*PUBLIC_CONDITIONS)
    areas = (
        select(func.unnest(Vendor.service_areas).label("name")).join(Vendor.category).where(*PUBLIC_CONDITIONS)
    )
    names = db.scalars(select(union(towns, areas).subquery().c.name)).all()
    # De-duplicate case-insensitively; prefer the capitalised spelling ("Kamareddy" over "kamareddy").
    unique: dict[str, str] = {}
    for raw in names:
        name = raw.strip()
        current = unique.get(name.lower())
        if current is None or (not current[:1].isupper() and name[:1].isupper()):
            unique[name.lower()] = name
    return sorted(unique.values(), key=str.lower)


def get_public_vendor(db: Session, slug: str) -> Vendor:
    vendor = db.scalar(
        _with_relations(select(Vendor).join(Vendor.category).where(Vendor.slug == slug, *PUBLIC_CONDITIONS))
    )
    if vendor is None:
        raise NotFoundError("Vendor not found")
    return vendor


# ---------- Listings ----------

def _paginate(db: Session, stmt: Select, params: PageParams, order_by: list) -> tuple[list[Vendor], int]:  # type: ignore[type-arg]
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(_with_relations(stmt).order_by(*order_by).offset(params.offset).limit(params.size)).all()
    return list(items), total


def list_public_vendors(
    db: Session,
    params: PageParams,
    *,
    category_slug: str | None = None,
    q: str | None = None,
    location: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    available_on: date | None = None,
    sort: VendorSort = "newest",
) -> tuple[list[Vendor], int]:
    stmt = select(Vendor).join(Vendor.category).where(*PUBLIC_CONDITIONS)
    if category_slug:
        stmt = stmt.where(ServiceCategory.slug == category_slug)
    if q and q.strip():
        term = q.strip()
        # Also match services offered (active package names), e.g. "drone" or "veg meals".
        matching_packages = select(VendorPackage.vendor_id).where(
            VendorPackage.is_active.is_(True), VendorPackage.name.icontains(term, autoescape=True)
        )
        stmt = stmt.where(
            or_(
                Vendor.business_name.icontains(term, autoescape=True),
                Vendor.description.icontains(term, autoescape=True),
                ServiceCategory.name.icontains(term, autoescape=True),
                Vendor.id.in_(matching_packages),
            )
        )
    if available_on is not None:
        # Only vendors who have themselves declared the date available. No entry = unknown, not free.
        stmt = stmt.where(
            Vendor.id.in_(
                select(VendorAvailability.vendor_id).where(
                    VendorAvailability.date == available_on,
                    VendorAvailability.availability_status == AvailabilityStatus.AVAILABLE,
                )
            )
        )
    if location and location.strip():
        term = location.strip()
        stmt = stmt.where(
            or_(
                Vendor.location.icontains(term, autoescape=True),
                func.array_to_string(Vendor.service_areas, " | ").icontains(term, autoescape=True),
            )
        )
    # Vendors without a published price never match a price filter (nothing is invented).
    if min_price is not None:
        stmt = stmt.where(Vendor.starting_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Vendor.starting_price <= max_price)

    order = {
        "newest": [Vendor.approved_at.desc().nulls_last(), Vendor.id.desc()],
        "price_low": [Vendor.starting_price.asc().nulls_last(), Vendor.id],
        "price_high": [Vendor.starting_price.desc().nulls_last(), Vendor.id],
        "name": [func.lower(Vendor.business_name), Vendor.id],
    }[sort]
    return _paginate(db, stmt, params, order)


def list_admin_vendors(
    db: Session,
    params: PageParams,
    *,
    status: ApprovalStatus | None = None,
    category_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> tuple[list[Vendor], int]:
    stmt = select(Vendor)
    if status is not None:
        stmt = stmt.where(Vendor.approval_status == status)
    if category_id is not None:
        stmt = stmt.where(Vendor.category_id == category_id)
    if is_active is not None:
        stmt = stmt.where(Vendor.is_active.is_(is_active))
    if search and search.strip():
        term = search.strip()
        stmt = stmt.where(
            or_(
                Vendor.business_name.icontains(term, autoescape=True),
                Vendor.location.icontains(term, autoescape=True),
                Vendor.contact_phone.icontains(term, autoescape=True),
                Vendor.contact_email.icontains(term, autoescape=True),
            )
        )
    # Oldest pending first, so the approval queue is handled in order.
    return _paginate(db, stmt, params, [Vendor.created_at.asc(), Vendor.id.asc()])


def count_by_status(db: Session) -> dict[str, int]:
    rows = db.execute(select(Vendor.approval_status, func.count()).group_by(Vendor.approval_status)).all()
    counts = {status.value: 0 for status in ApprovalStatus}
    counts.update({status.value: count for status, count in rows})
    return counts


# ---------- Create / update ----------

def _require_active_category(db: Session, category_id: int) -> None:
    category = db.get(ServiceCategory, category_id)
    if category is None or not category.is_active:
        raise BusinessRuleError("Select a valid, active category")


def _ensure_unique_name(db: Session, category_id: int, business_name: str, exclude_id: int | None = None) -> None:
    stmt = select(Vendor.id).where(
        Vendor.category_id == category_id, func.lower(Vendor.business_name) == business_name.lower()
    )
    if exclude_id is not None:
        stmt = stmt.where(Vendor.id != exclude_id)
    if db.scalar(stmt):
        raise ConflictError("A vendor with this business name already exists in this category")


def create_vendor(db: Session, data: VendorCreate, *, owner: User | None, actor: User) -> Vendor:
    """Create a profile. New profiles are always `pending` until an administrator approves them."""
    _require_active_category(db, data.category_id)
    _ensure_unique_name(db, data.category_id, data.business_name)
    if owner is not None and get_vendor_for_user(db, owner) is not None:
        raise ConflictError("This account already has a business profile")

    vendor = Vendor(
        **data.model_dump(),
        slug=unique_slug(db, Vendor.slug, data.business_name, fallback="vendor"),
        user_id=owner.id if owner else None,
        created_by_id=actor.id,
        approval_status=ApprovalStatus.PENDING,
    )
    db.add(vendor)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A vendor with these details already exists")

    record_audit(db, actor_id=actor.id, action="vendor.created", entity_type="vendor", entity_id=vendor.id,
                 details={"by_admin": actor.role == UserRole.ADMIN, "category_id": vendor.category_id})
    db.commit()
    return get_vendor(db, vendor.id)


def update_vendor(db: Session, vendor: Vendor, data: VendorUpdate | AdminVendorUpdate, actor: User) -> Vendor:
    changes = data.model_dump(exclude_unset=True)
    for field in (*REQUIRED_FIELDS, "service_areas", "is_active"):
        if field in changes and changes[field] is None:
            if field in REQUIRED_FIELDS:
                raise BusinessRuleError(f"{field.replace('_', ' ').capitalize()} cannot be empty")
            changes.pop(field)

    category_changed = "category_id" in changes and changes["category_id"] != vendor.category_id
    if category_changed:
        _require_active_category(db, changes["category_id"])
    if category_changed or ("business_name" in changes and changes["business_name"] != vendor.business_name):
        _ensure_unique_name(
            db, changes.get("category_id", vendor.category_id), changes.get("business_name", vendor.business_name),
            exclude_id=vendor.id,
        )

    for field, value in changes.items():
        setattr(vendor, field, value)

    status_change = None
    if actor.role != UserRole.ADMIN:
        if vendor.approval_status == ApprovalStatus.REJECTED:
            # Editing a rejected profile re-submits it for review.
            vendor.approval_status = ApprovalStatus.PENDING
            vendor.status_reason = None
            status_change = "resubmitted"
        elif vendor.approval_status == ApprovalStatus.APPROVED and category_changed:
            vendor.approval_status = ApprovalStatus.PENDING
            status_change = "category_changed_needs_review"

    record_audit(db, actor_id=actor.id, action="vendor.updated", entity_type="vendor", entity_id=vendor.id,
                 details={"fields": sorted(changes), "status_change": status_change})
    db.commit()
    return get_vendor(db, vendor.id)


# ---------- Approval workflow ----------

def change_approval(db: Session, vendor: Vendor, action: str, admin: User, reason: str | None) -> Vendor:
    allowed_from, target, audit_action = APPROVAL_TRANSITIONS[action]
    if vendor.approval_status not in allowed_from:
        raise BusinessRuleError(f"Cannot {action} a vendor whose status is '{vendor.approval_status.value}'")
    reason = (reason or "").strip() or None
    if target in (ApprovalStatus.REJECTED, ApprovalStatus.SUSPENDED) and not reason:
        raise BusinessRuleError("Please give a reason so the vendor knows what to fix")

    previous = vendor.approval_status
    vendor.approval_status = target
    if target == ApprovalStatus.APPROVED:
        vendor.approved_at = _now()
        vendor.approved_by_id = admin.id
        vendor.status_reason = None
    else:
        vendor.status_reason = reason

    record_audit(db, actor_id=admin.id, action=audit_action, entity_type="vendor", entity_id=vendor.id,
                 details={"from": previous.value, "to": target.value, "reason": reason})
    db.commit()
    return get_vendor(db, vendor.id)


def set_verification(db: Session, vendor: Vendor, admin: User, is_verified: bool, notes: str | None) -> Vendor:
    vendor.is_verified = is_verified
    vendor.verified_at = _now() if is_verified else None
    vendor.verification_notes = (notes or "").strip() or None
    record_audit(db, actor_id=admin.id, action="vendor.verified" if is_verified else "vendor.unverified",
                 entity_type="vendor", entity_id=vendor.id)
    db.commit()
    return get_vendor(db, vendor.id)


# ---------- Ownership claim for admin-created profiles ----------

def _normalize_code(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def issue_claim_code(db: Session, vendor: Vendor, admin: User) -> tuple[str, datetime]:
    """Create a one-time code. Share it only with the verified business owner."""
    if vendor.user_id is not None:
        raise BusinessRuleError("This vendor profile is already linked to an account")
    raw = "".join(secrets.choice(CLAIM_ALPHABET) for _ in range(10))
    code = f"{raw[:5]}-{raw[5:]}"
    expires_at = _now() + timedelta(days=settings.CLAIM_CODE_EXPIRE_DAYS)
    vendor.claim_code_hash = hash_token(_normalize_code(code))
    vendor.claim_code_expires_at = expires_at
    record_audit(db, actor_id=admin.id, action="vendor.claim_code_issued", entity_type="vendor", entity_id=vendor.id)
    db.commit()
    return code, expires_at


def claim_vendor(db: Session, user: User, code: str) -> Vendor:
    if get_vendor_for_user(db, user) is not None:
        raise ConflictError("Your account already has a business profile")
    vendor = db.scalar(
        select(Vendor)
        .where(Vendor.claim_code_hash == hash_token(_normalize_code(code)))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        vendor is None
        or vendor.user_id is not None
        or vendor.claim_code_expires_at is None
        or vendor.claim_code_expires_at <= _now()
    ):
        raise BusinessRuleError("This code is invalid or has expired. Ask the administrator for a new one.")

    vendor.user_id = user.id
    vendor.claim_code_hash = None
    vendor.claim_code_expires_at = None
    record_audit(db, actor_id=user.id, action="vendor.claimed", entity_type="vendor", entity_id=vendor.id)
    db.commit()
    return get_vendor(db, vendor.id)
