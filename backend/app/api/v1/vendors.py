"""Public, read-only vendor endpoints. Only approved + active vendors in active categories."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.presenters import portfolio_read, vendor_public
from app.db.session import get_db
from app.dependencies.pagination import PageParams, get_page_params
from app.schemas.common import Page
from app.schemas.package import PackageRead
from app.schemas.portfolio import AvailabilityRead, PortfolioRead
from app.schemas.vendor import VendorPublic
from app.services import availability as availability_service
from app.services import packages as package_service
from app.services import portfolio as portfolio_service
from app.services import vendors as vendor_service
from app.services.storage import MediaStorage, get_storage
from app.services.vendors import VendorSort

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=Page[VendorPublic])
def list_vendors(
    category: str | None = Query(default=None, max_length=90, description="Category slug, e.g. photography"),
    q: str | None = Query(default=None, max_length=100, description="Search business name and description"),
    location: str | None = Query(default=None, max_length=100, description="Town or service area"),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    sort: VendorSort = "newest",
    params: PageParams = Depends(get_page_params),
    db: Session = Depends(get_db),
    storage: MediaStorage = Depends(get_storage),
) -> Page[VendorPublic]:
    items, total = vendor_service.list_public_vendors(
        db, params, category_slug=category, q=q, location=location,
        min_price=min_price, max_price=max_price, sort=sort,
    )
    return Page[VendorPublic].build([vendor_public(v, storage) for v in items], total, params.page, params.size)


@router.get("/{slug}", response_model=VendorPublic)
def get_vendor(slug: str, db: Session = Depends(get_db), storage: MediaStorage = Depends(get_storage)) -> VendorPublic:
    return vendor_public(vendor_service.get_public_vendor(db, slug), storage)


@router.get("/{slug}/packages", response_model=list[PackageRead])
def get_vendor_packages(slug: str, db: Session = Depends(get_db)):  # type: ignore[no-untyped-def]
    vendor = vendor_service.get_public_vendor(db, slug)
    return package_service.list_packages(db, vendor, include_inactive=False)


@router.get("/{slug}/portfolio", response_model=list[PortfolioRead])
def get_vendor_portfolio(  # type: ignore[no-untyped-def]
    slug: str, db: Session = Depends(get_db), storage: MediaStorage = Depends(get_storage)
):
    vendor = vendor_service.get_public_vendor(db, slug)
    return [portfolio_read(i, storage) for i in portfolio_service.list_portfolio(db, vendor)]


@router.get("/{slug}/availability", response_model=list[AvailabilityRead])
def get_vendor_availability(  # type: ignore[no-untyped-def]
    slug: str,
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Vendor-declared availability only. Dates without an entry are unknown, not free."""
    vendor = vendor_service.get_public_vendor(db, slug)
    start, end = availability_service.resolve_range(start, end)
    return availability_service.list_availability(db, vendor, start, end)
