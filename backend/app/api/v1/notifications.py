from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PageParams, get_page_params
from app.models.user import User
from app.schemas.common import Page
from app.services import notifications as notification_service

router = APIRouter(prefix="/me/notifications", tags=["notifications"])


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    body: str
    link: str | None
    is_read: bool
    created_at: datetime


class UnreadCount(BaseModel):
    count: int


@router.get("", response_model=Page[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    params: PageParams = Depends(get_page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[NotificationRead]:
    items, total = notification_service.list_notifications(db, user, params, unread_only=unread_only)
    return Page[NotificationRead].build([NotificationRead.model_validate(n) for n in items], total, params.page, params.size)


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UnreadCount:
    return UnreadCount(count=notification_service.unread_count(db, user))


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    return notification_service.mark_read(db, user, notification_id)


@router.post("/read-all", status_code=status.HTTP_200_OK, response_model=UnreadCount)
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UnreadCount:
    """Marks everything as read. Returns how many notifications were updated."""
    return UnreadCount(count=notification_service.mark_all_read(db, user))
