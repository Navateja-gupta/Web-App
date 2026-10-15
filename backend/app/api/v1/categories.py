from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models.category import ServiceCategory
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services import categories as category_service

public_router = APIRouter(prefix="/categories", tags=["categories"])
admin_router = APIRouter(prefix="/admin/categories", tags=["admin: categories"])


def _read(category: ServiceCategory, vendor_count: int = 0) -> CategoryRead:
    return CategoryRead.model_validate(category).model_copy(update={"vendor_count": vendor_count})


# ---------- Public ----------

@public_router.get("", response_model=list[CategoryRead])
def list_active_categories(db: Session = Depends(get_db)) -> list[CategoryRead]:
    """Active categories with the number of approved vendors in each."""
    return [_read(c, n) for c, n in category_service.list_categories(db, include_inactive=False)]


@public_router.get("/{slug}", response_model=CategoryRead)
def get_category(slug: str, db: Session = Depends(get_db)) -> CategoryRead:
    category, count = category_service.get_active_category_by_slug(db, slug)
    return _read(category, count)


# ---------- Admin ----------

@admin_router.get("", response_model=list[CategoryRead])
def admin_list_categories(_admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[CategoryRead]:
    return [_read(c, n) for c, n in category_service.list_categories(db, include_inactive=True)]


@admin_router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> CategoryRead:
    return _read(category_service.create_category(db, data, admin))


@admin_router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, data: CategoryUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> CategoryRead:
    category = category_service.update_category(db, category_service.get_category(db, category_id), data, admin)
    return _read(category, category_service.approved_vendor_counts(db).get(category.id, 0))


@admin_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    """Only allowed when no vendor uses the category; otherwise deactivate it with PATCH."""
    category_service.delete_category(db, category_service.get_category(db, category_id), admin)
