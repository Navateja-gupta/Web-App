"""The signed-in vendor's own business profile."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.presenters import vendor_owner
from app.api.v1.vendor_resources import VendorAccess, build_vendor_resource_router
from app.core.errors import NotFoundError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.dependencies.auth import require_vendor
from app.models.user import User
from app.schemas.vendor import ClaimRequest, VendorCreate, VendorOwnerRead, VendorUpdate
from app.services import vendors as vendor_service
from app.services.storage import MediaStorage, get_storage

router = APIRouter(prefix="/me/vendor", tags=["vendor: my business"])

claim_rate_limit = rate_limit(10, 3600)


def my_vendor_access(user: User = Depends(require_vendor), db: Session = Depends(get_db)) -> VendorAccess:
    vendor = vendor_service.get_vendor_for_user(db, user)
    if vendor is None:
        raise NotFoundError("You have not created a business profile yet")
    return VendorAccess(vendor=vendor, actor=user)


@router.get("", response_model=VendorOwnerRead)
def get_my_vendor(
    access: VendorAccess = Depends(my_vendor_access), storage: MediaStorage = Depends(get_storage)
) -> VendorOwnerRead:
    return vendor_owner(access.vendor, storage)


@router.post("", response_model=VendorOwnerRead, status_code=status.HTTP_201_CREATED)
def create_my_vendor(
    data: VendorCreate,
    user: User = Depends(require_vendor),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> VendorOwnerRead:
    """Create your business profile. It stays `pending` until an administrator approves it."""
    vendor = vendor_service.create_vendor(db, data, owner=user, actor=user)
    return vendor_owner(vendor, storage)


@router.patch("", response_model=VendorOwnerRead)
def update_my_vendor(
    data: VendorUpdate,
    access: VendorAccess = Depends(my_vendor_access),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> VendorOwnerRead:
    return vendor_owner(vendor_service.update_vendor(db, access.vendor, data, access.actor), storage)


@router.post("/claim", response_model=VendorOwnerRead, dependencies=[Depends(claim_rate_limit)])
def claim_vendor_profile(
    data: ClaimRequest,
    user: User = Depends(require_vendor),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> VendorOwnerRead:
    """Link a profile the administrator created for you, using the one-time code they gave you."""
    return vendor_owner(vendor_service.claim_vendor(db, user, data.code), storage)


router.include_router(build_vendor_resource_router(my_vendor_access))
