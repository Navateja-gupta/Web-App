from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.text import slugify, unique_slug
from app.models.category import ServiceCategory
from app.models.enums import ApprovalStatus
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.audit import record_audit


def approved_vendor_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Vendor.category_id, func.count())
        .where(Vendor.approval_status == ApprovalStatus.APPROVED, Vendor.is_active.is_(True))
        .group_by(Vendor.category_id)
    ).all()
    return {category_id: count for category_id, count in rows}


def list_categories(db: Session, *, include_inactive: bool) -> list[tuple[ServiceCategory, int]]:
    stmt = select(ServiceCategory).order_by(ServiceCategory.display_order, ServiceCategory.name)
    if not include_inactive:
        stmt = stmt.where(ServiceCategory.is_active.is_(True))
    counts = approved_vendor_counts(db)
    return [(category, counts.get(category.id, 0)) for category in db.scalars(stmt)]


def get_category(db: Session, category_id: int) -> ServiceCategory:
    category = db.get(ServiceCategory, category_id)
    if category is None:
        raise NotFoundError("Category not found")
    return category


def get_active_category_by_slug(db: Session, slug: str) -> tuple[ServiceCategory, int]:
    category = db.scalar(
        select(ServiceCategory).where(ServiceCategory.slug == slug, ServiceCategory.is_active.is_(True))
    )
    if category is None:
        raise NotFoundError("Category not found")
    return category, approved_vendor_counts(db).get(category.id, 0)


def _ensure_name_available(db: Session, name: str, exclude_id: int | None = None) -> None:
    conditions = [func.lower(ServiceCategory.name) == name.lower()]
    if slugify(name):
        conditions.append(ServiceCategory.slug == slugify(name))
    stmt = select(ServiceCategory.id).where(or_(*conditions))
    if exclude_id is not None:
        stmt = stmt.where(ServiceCategory.id != exclude_id)
    if db.scalar(stmt):
        raise ConflictError("A category with this name already exists")


def create_category(db: Session, data: CategoryCreate, admin: User) -> ServiceCategory:
    _ensure_name_available(db, data.name)
    category = ServiceCategory(
        **data.model_dump(),
        slug=unique_slug(db, ServiceCategory.slug, data.name, fallback="category"),
    )
    db.add(category)
    db.flush()
    record_audit(db, actor_id=admin.id, action="category.created", entity_type="category", entity_id=category.id,
                 details={"name": category.name})
    db.commit()
    return category


def update_category(db: Session, category: ServiceCategory, data: CategoryUpdate, admin: User) -> ServiceCategory:
    changes = data.model_dump(exclude_unset=True)
    if changes.get("name") is None:
        changes.pop("name", None)
    if changes.get("display_order") is None:
        changes.pop("display_order", None)
    if changes.get("is_active") is None:
        changes.pop("is_active", None)
    if "name" in changes and changes["name"].lower() != category.name.lower():
        _ensure_name_available(db, changes["name"], exclude_id=category.id)

    # The slug is kept stable so existing links keep working after a rename.
    for field, value in changes.items():
        setattr(category, field, value)

    action = "category.updated"
    if changes.keys() == {"is_active"}:
        action = "category.activated" if changes["is_active"] else "category.deactivated"
    record_audit(db, actor_id=admin.id, action=action, entity_type="category", entity_id=category.id,
                 details={"fields": sorted(changes)})
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: ServiceCategory, admin: User) -> None:
    """Hard delete only when nothing references the category; otherwise deactivate it."""
    if db.scalar(select(Vendor.id).where(Vendor.category_id == category.id).limit(1)):
        raise ConflictError("This category has vendors. Deactivate it instead to keep their history.")
    record_audit(db, actor_id=admin.id, action="category.deleted", entity_type="category", entity_id=category.id,
                 details={"name": category.name})
    db.delete(category)
    db.commit()
