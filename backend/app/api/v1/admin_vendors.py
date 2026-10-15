from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.presenters import vendor_admin
from app.api.v1.vendor_resources import VendorAccess, build_vendor_resource_router
from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.dependencies.pagination import PageParams, get_page_params
from app.models.enums import ApprovalStatus
from app.models.user import User
from app.schemas.common import Page
from app.schemas.vendor import (
    AdminVendorUpdate,
    ApprovalDecision,
    ClaimCodeRead,
    VendorAdminRead,
    VendorCreate,
    VerificationUpdate,
)
from app.services import vendors as vendor_service
from app.services.storage import MediaStorage, get_storage

router = APIRouter(prefix="/admin/vendors", tags=["admin: vendors"])


def admin_vendor_access(
    vendor_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> VendorAccess:
    return VendorAccess(vendor=vendor_service.get_vendor(db, vendor_id), actor=admin)


@router.get("", response_model=Page[VendorAdminRead])
def list_vendors(
    approval_status: ApprovalStatus | None = None,
    category_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = Query(default=None, max_length=100),
    params: PageParams = Depends(get_page_params),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> Page[VendorAdminRead]:
    items, total = vendor_service.list_admin_vendors(
        db, params, status=approval_status, category_id=category_id, is_active=is_active, search=search
    )
    return Page[VendorAdminRead].build([vendor_admin(v, storage) for v in items], total, params.page, params.size)


@router.get("/status-counts", response_model=dict[str, int])
def status_counts(_admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict[str, int]:
    return vendor_service.count_by_status(db)


@router.post("", response_model=VendorAdminRead, status_code=status.HTTP_201_CREATED)
def create_vendor(
    data: VendorCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> VendorAdminRead:
    """Add a vendor on their behalf (with their consent). Starts as `pending`; approve it to publish."""
    return vendor_admin(vendor_service.create_vendor(db, data, owner=None, actor=admin), storage)


@router.get("/{vendor_id}", response_model=VendorAdminRead)
def get_vendor(
    access: VendorAccess = Depends(admin_vendor_access), storage: MediaStorage = Depends(get_storage)
) -> VendorAdminRead:
    return vendor_admin(access.vendor, storage)


@router.patch("/{vendor_id}", response_model=VendorAdminRead)
def update_vendor(
    data: AdminVendorUpdate,
    access: VendorAccess = Depends(admin_vendor_access),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> VendorAdminRead:
    return vendor_admin(vendor_service.update_vendor(db, access.vendor, data, access.actor), storage)


def _decision_route(action: str):  # type: ignore[no-untyped-def]
    def handler(
        data: ApprovalDecision | None = None,
        access: VendorAccess = Depends(admin_vendor_access),
        db: Session = Depends(get_db),
        storage: MediaStorage = Depends(get_storage),
    ) -> VendorAdminRead:
        reason = data.reason if data else None
        return vendor_admin(vendor_service.change_approval(db, access.vendor, action, access.actor, reason), storage)

    handler.__name__ = f"{action}_vendor"
    return handler


router.post("/{vendor_id}/approve", response_model=VendorAdminRead, summary="Approve vendor (publish listing)")(
    _decision_route("approve")
)
router.post("/{vendor_id}/reject", response_model=VendorAdminRead, summary="Reject vendor (reason required)")(
    _decision_route("reject")
)
router.post("/{vendor_id}/suspend", response_model=VendorAdminRead, summary="Suspend vendor (reason required)")(
    _decision_route("suspend")
)


@router.post("/{vendor_id}/verification", response_model=VendorAdminRead)
def set_verification(
    data: VerificationUpdate,
    access: VendorAccess = Depends(admin_vendor_access),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> VendorAdminRead:
    """Mark that you have checked the vendor's identity/business. Only set after a real check."""
    vendor = vendor_service.set_verification(db, access.vendor, access.actor, data.is_verified, data.notes)
    return vendor_admin(vendor, storage)


@router.post("/{vendor_id}/claim-code", response_model=ClaimCodeRead)
def issue_claim_code(access: VendorAccess = Depends(admin_vendor_access), db: Session = Depends(get_db)) -> ClaimCodeRead:
    """One-time code for the business owner to link this profile to their vendor account.

    The code is shown only once. Give it to the owner through a channel you have verified.
    """
    code, expires_at = vendor_service.issue_claim_code(db, access.vendor, access.actor)
    return ClaimCodeRead(code=code, expires_at=expires_at)


router.include_router(build_vendor_resource_router(admin_vendor_access), prefix="/{vendor_id}")
