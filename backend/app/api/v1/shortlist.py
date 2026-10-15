from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.presenters import vendor_public
from app.db.session import get_db
from app.dependencies.auth import require_customer
from app.models.user import User
from app.schemas.vendor import VendorPublic
from app.services import shortlist as shortlist_service
from app.services.storage import MediaStorage, get_storage

router = APIRouter(prefix="/me/shortlist", tags=["customer: shortlist"])


class ShortlistItem(BaseModel):
    vendor: VendorPublic
    added_at: datetime


@router.get("", response_model=list[ShortlistItem])
def list_shortlist(
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> list[ShortlistItem]:
    return [
        ShortlistItem(vendor=vendor_public(vendor, storage), added_at=added_at)
        for vendor, added_at in shortlist_service.list_shortlist(db, customer)
    ]


@router.get("/ids", response_model=list[int])
def list_shortlist_ids(customer: User = Depends(require_customer), db: Session = Depends(get_db)) -> list[int]:
    """Just the vendor ids, so listing pages can show which vendors are saved."""
    return shortlist_service.shortlisted_ids(db, customer)


@router.put("/{vendor_id}", response_model=ShortlistItem)
def add_to_shortlist(
    vendor_id: int,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> ShortlistItem:
    vendor, added_at = shortlist_service.add_to_shortlist(db, customer, vendor_id)
    return ShortlistItem(vendor=vendor_public(vendor, storage), added_at=added_at)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_shortlist(
    vendor_id: int, customer: User = Depends(require_customer), db: Session = Depends(get_db)
) -> None:
    shortlist_service.remove_from_shortlist(db, customer, vendor_id)
