from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.category import ServiceCategory
from app.models.enums import PlanItemStatus
from app.models.package import VendorPackage
from app.models.user import User
from app.models.vendor import Vendor
from app.models.wedding_plan import WeddingPlan, WeddingPlanItem
from app.schemas.wedding_plan import PlanItemCreate, PlanItemUpdate, WeddingPlanCreate, WeddingPlanUpdate

MAX_PLANS = 20
MAX_ITEMS = 200
ZERO = Decimal("0")


def budget_summary(plan: WeddingPlan) -> dict[str, object]:
    """Budget maths for a plan.

    committed = actual cost where known, otherwise the estimate; cancelled items are ignored.
    remaining = estimated budget - committed (only when a budget is set).
    """
    active = [i for i in plan.items if i.status != PlanItemStatus.CANCELLED]
    total_estimated = sum((i.estimated_cost for i in active), ZERO)
    total_actual = sum((i.actual_cost for i in active if i.actual_cost is not None), ZERO)
    committed = sum((i.actual_cost if i.actual_cost is not None else i.estimated_cost for i in active), ZERO)
    remaining = plan.estimated_budget - committed if plan.estimated_budget is not None else None
    by_status = {status.value: 0 for status in PlanItemStatus}
    for item in plan.items:
        by_status[item.status.value] += 1
    return {
        "estimated_budget": plan.estimated_budget,
        "total_estimated": total_estimated,
        "total_actual": total_actual,
        "committed": committed,
        "remaining": remaining,
        "over_budget": remaining is not None and remaining < 0,
        "item_count": len(plan.items),
        "by_status": by_status,
    }


def _query() -> Select:  # type: ignore[type-arg]
    return (
        select(WeddingPlan)
        .options(
            selectinload(WeddingPlan.items).selectinload(WeddingPlanItem.category),
            selectinload(WeddingPlan.items).selectinload(WeddingPlanItem.vendor),
        )
        .execution_options(populate_existing=True)
    )


def list_plans(db: Session, customer: User) -> list[WeddingPlan]:
    return list(
        db.scalars(
            _query()
            .where(WeddingPlan.customer_id == customer.id)
            .order_by(WeddingPlan.event_date.asc().nulls_last(), WeddingPlan.id)
        )
    )


def get_plan(db: Session, customer: User, plan_id: int) -> WeddingPlan:
    plan = db.scalar(_query().where(WeddingPlan.id == plan_id, WeddingPlan.customer_id == customer.id))
    if plan is None:
        raise NotFoundError("Wedding plan not found")
    return plan


def create_plan(db: Session, customer: User, data: WeddingPlanCreate) -> WeddingPlan:
    count = db.scalar(select(func.count()).where(WeddingPlan.customer_id == customer.id)) or 0
    if count >= MAX_PLANS:
        raise BusinessRuleError(f"You can have at most {MAX_PLANS} events")
    plan = WeddingPlan(customer_id=customer.id, **data.model_dump())
    db.add(plan)
    db.commit()
    return get_plan(db, customer, plan.id)


def update_plan(db: Session, customer: User, plan_id: int, data: WeddingPlanUpdate) -> WeddingPlan:
    plan = get_plan(db, customer, plan_id)
    changes = data.model_dump(exclude_unset=True)
    if "event_name" in changes and changes["event_name"] is None:
        raise BusinessRuleError("Event name cannot be empty")
    for field, value in changes.items():
        setattr(plan, field, value)
    db.commit()
    return get_plan(db, customer, plan.id)


def delete_plan(db: Session, customer: User, plan_id: int) -> None:
    """Deletes the plan and its budget lines. Linked bookings/enquiries are kept (link set to NULL)."""
    plan = get_plan(db, customer, plan_id)
    db.delete(plan)
    db.commit()


def _validate_links(db: Session, category_id: int | None, vendor_id: int | None, package_id: int | None) -> None:
    if category_id is not None and db.get(ServiceCategory, category_id) is None:
        raise NotFoundError("Category not found")
    if vendor_id is not None and db.get(Vendor, vendor_id) is None:
        raise NotFoundError("Vendor not found")
    if package_id is not None:
        package = db.get(VendorPackage, package_id)
        if package is None or (vendor_id is not None and package.vendor_id != vendor_id):
            raise NotFoundError("Package not found for this vendor")


def add_item(db: Session, customer: User, plan_id: int, data: PlanItemCreate) -> WeddingPlan:
    plan = get_plan(db, customer, plan_id)
    if len(plan.items) >= MAX_ITEMS:
        raise BusinessRuleError(f"A plan can have at most {MAX_ITEMS} items")
    _validate_links(db, data.category_id, data.vendor_id, data.package_id)
    db.add(WeddingPlanItem(wedding_plan_id=plan.id, **data.model_dump()))
    db.commit()
    return get_plan(db, customer, plan.id)


def _get_item(plan: WeddingPlan, item_id: int) -> WeddingPlanItem:
    for item in plan.items:
        if item.id == item_id:
            return item
    raise NotFoundError("Budget item not found")


def update_item(db: Session, customer: User, plan_id: int, item_id: int, data: PlanItemUpdate) -> WeddingPlan:
    plan = get_plan(db, customer, plan_id)
    item = _get_item(plan, item_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("description", "estimated_cost", "status"):
        if field in changes and changes[field] is None:
            raise BusinessRuleError(f"{field.replace('_', ' ').capitalize()} cannot be empty")
    _validate_links(
        db,
        changes.get("category_id", item.category_id),
        changes.get("vendor_id", item.vendor_id),
        changes.get("package_id", item.package_id),
    )
    for field, value in changes.items():
        setattr(item, field, value)
    db.commit()
    return get_plan(db, customer, plan.id)


def delete_item(db: Session, customer: User, plan_id: int, item_id: int) -> WeddingPlan:
    plan = get_plan(db, customer, plan_id)
    db.delete(_get_item(plan, item_id))
    db.commit()
    return get_plan(db, customer, plan.id)
