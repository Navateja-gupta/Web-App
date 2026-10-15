"""Packages, portfolio and availability management routes.

Built once and mounted twice:
  * /me/vendor/...                 -> the signed-in vendor's own profile
  * /admin/vendors/{vendor_id}/... -> any profile, for administrators
The `access` dependency decides which vendor is being managed, so ownership is
enforced in exactly one place per mount.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.v1.presenters import portfolio_read
from app.core.config import settings
from app.core.errors import BusinessRuleError
from app.db.session import get_db
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.package import PackageCreate, PackageRead, PackageUpdate
from app.schemas.portfolio import AvailabilityRead, AvailabilitySet, PortfolioRead, PortfolioUpdate
from app.services import availability as availability_service
from app.services import packages as package_service
from app.services import portfolio as portfolio_service
from app.services.storage import MediaStorage, get_storage

ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass
class VendorAccess:
    vendor: Vendor
    actor: User


def read_upload(file: UploadFile) -> bytes:
    # Content-Type is only a quick first check; the real check decodes the image.
    if file.content_type not in ALLOWED_UPLOAD_TYPES:
        raise BusinessRuleError("Upload a JPEG, PNG or WebP image")
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise BusinessRuleError(f"Images must be {settings.MAX_UPLOAD_MB} MB or smaller")
    return data


def build_vendor_resource_router(access_dependency: Callable[..., VendorAccess]) -> APIRouter:
    router = APIRouter()

    # ---------- Packages ----------

    @router.get("/packages", response_model=list[PackageRead])
    def list_packages(access: VendorAccess = Depends(access_dependency), db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
        return package_service.list_packages(db, access.vendor, include_inactive=True)

    @router.post("/packages", response_model=PackageRead, status_code=status.HTTP_201_CREATED)
    def create_package(  # type: ignore[no-untyped-def]
        data: PackageCreate, access: VendorAccess = Depends(access_dependency), db: Session = Depends(get_db)
    ):
        return package_service.create_package(db, access.vendor, data, access.actor)

    @router.patch("/packages/{package_id}", response_model=PackageRead)
    def update_package(  # type: ignore[no-untyped-def]
        package_id: int,
        data: PackageUpdate,
        access: VendorAccess = Depends(access_dependency),
        db: Session = Depends(get_db),
    ):
        return package_service.update_package(db, access.vendor, package_id, data, access.actor)

    @router.delete("/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_package(  # type: ignore[no-untyped-def]
        package_id: int, access: VendorAccess = Depends(access_dependency), db: Session = Depends(get_db)
    ):
        package_service.delete_package(db, access.vendor, package_id, access.actor)

    # ---------- Portfolio ----------

    @router.get("/portfolio", response_model=list[PortfolioRead])
    def list_portfolio(  # type: ignore[no-untyped-def]
        access: VendorAccess = Depends(access_dependency),
        db: Session = Depends(get_db),
        storage: MediaStorage = Depends(get_storage),
    ):
        return [portfolio_read(i, storage) for i in portfolio_service.list_portfolio(db, access.vendor)]

    @router.post("/portfolio", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
    def upload_photo(  # type: ignore[no-untyped-def]
        file: UploadFile = File(..., description="JPEG, PNG or WebP"),
        caption: str | None = Form(default=None, max_length=255),
        access: VendorAccess = Depends(access_dependency),
        db: Session = Depends(get_db),
        storage: MediaStorage = Depends(get_storage),
    ):
        item = portfolio_service.add_image(db, storage, access.vendor, read_upload(file), caption, access.actor)
        return portfolio_read(item, storage)

    @router.patch("/portfolio/{item_id}", response_model=PortfolioRead)
    def update_photo(  # type: ignore[no-untyped-def]
        item_id: int,
        data: PortfolioUpdate,
        access: VendorAccess = Depends(access_dependency),
        db: Session = Depends(get_db),
        storage: MediaStorage = Depends(get_storage),
    ):
        return portfolio_read(portfolio_service.update_item(db, access.vendor, item_id, data), storage)

    @router.delete("/portfolio/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_photo(  # type: ignore[no-untyped-def]
        item_id: int,
        access: VendorAccess = Depends(access_dependency),
        db: Session = Depends(get_db),
        storage: MediaStorage = Depends(get_storage),
    ):
        portfolio_service.delete_item(db, storage, access.vendor, item_id, access.actor)

    # ---------- Availability ----------

    @router.get("/availability", response_model=list[AvailabilityRead])
    def list_availability(  # type: ignore[no-untyped-def]
        start: date | None = Query(default=None),
        end: date | None = Query(default=None),
        access: VendorAccess = Depends(access_dependency),
        db: Session = Depends(get_db),
    ):
        start, end = availability_service.resolve_range(start, end)
        return availability_service.list_availability(db, access.vendor, start, end)

    @router.put("/availability/{day}", response_model=AvailabilityRead)
    def set_availability(  # type: ignore[no-untyped-def]
        day: date,
        data: AvailabilitySet,
        access: VendorAccess = Depends(access_dependency),
        db: Session = Depends(get_db),
    ):
        return availability_service.set_availability(db, access.vendor, day, data)

    @router.delete("/availability/{day}", status_code=status.HTTP_204_NO_CONTENT)
    def clear_availability(  # type: ignore[no-untyped-def]
        day: date, access: VendorAccess = Depends(access_dependency), db: Session = Depends(get_db)
    ):
        availability_service.clear_availability(db, access.vendor, day)

    return router
