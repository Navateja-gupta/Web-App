from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.dependencies.pagination import PageParams
from app.models.enums import UserRole
from app.models.user import User
from app.services.audit import record_audit
from app.services.auth import revoke_all_sessions


def list_users(
    db: Session,
    params: PageParams,
    *,
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> tuple[list[User], int]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if search and search.strip():
        term = search.strip()
        stmt = stmt.where(
            or_(
                User.full_name.icontains(term, autoescape=True),
                User.email.icontains(term, autoescape=True),
                User.phone.icontains(term, autoescape=True),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(User.created_at.desc(), User.id.desc()).offset(params.offset).limit(params.size)
    ).all()
    return list(items), total


def set_user_active(db: Session, admin: User, user_id: int, is_active: bool) -> User:
    if user_id == admin.id:
        raise BusinessRuleError("You cannot change the status of your own account")
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.is_active == is_active:
        return user

    user.is_active = is_active
    if not is_active:
        revoke_all_sessions(db, user.id)
    record_audit(
        db,
        actor_id=admin.id,
        action="user.activated" if is_active else "user.deactivated",
        entity_type="user",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user
