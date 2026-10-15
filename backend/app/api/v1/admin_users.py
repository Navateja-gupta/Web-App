from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.dependencies.pagination import PageParams, get_page_params
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import ResetLinkRead, UserRead, UserStatusUpdate
from app.services import password_reset as password_reset_service
from app.services import users as user_service

router = APIRouter(prefix="/admin/users", tags=["admin: users"])


@router.get("", response_model=Page[UserRead])
def list_users(
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = Query(default=None, max_length=100),
    params: PageParams = Depends(get_page_params),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[UserRead]:
    items, total = user_service.list_users(db, params, role=role, is_active=is_active, search=search)
    return Page[UserRead].build(
        [UserRead.model_validate(u) for u in items], total, params.page, params.size
    )


@router.post("/{user_id}/password-reset-link", response_model=ResetLinkRead)
def create_password_reset_link(
    user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> ResetLinkRead:
    """One-time link (valid 24 h) for a user who forgot their password.

    Share it only with that person, directly. Anyone holding the link can set a new password.
    """
    url, expires_at, user = password_reset_service.create_reset_link(db, admin, user_id)
    return ResetLinkRead(reset_url=url, expires_at=expires_at, user_email=user.email)


@router.patch("/{user_id}", response_model=UserRead)
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    """Activate or deactivate an account. Deactivation signs the user out everywhere."""
    return user_service.set_user_active(db, admin, user_id, data.is_active)
