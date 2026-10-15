"""Convert ORM objects into response schemas that need extra context (e.g. media URLs)."""

from app.models.vendor import Vendor, VendorPortfolio
from app.schemas.portfolio import PortfolioRead
from app.schemas.vendor import VendorAdminRead, VendorOwnerRead, VendorPublic
from app.services.storage import MediaStorage


def portfolio_read(item: VendorPortfolio, storage: MediaStorage) -> PortfolioRead:
    return PortfolioRead(
        id=item.id,
        url=storage.url(item.media_path),
        media_type=item.media_type,
        caption=item.caption,
        display_order=item.display_order,
        created_at=item.created_at,
    )


def _cover(vendor: Vendor, storage: MediaStorage) -> str | None:
    items = sorted(vendor.portfolio_items, key=lambda i: (i.display_order, i.id))
    return storage.url(items[0].media_path) if items else None


def vendor_public(vendor: Vendor, storage: MediaStorage) -> VendorPublic:
    return VendorPublic.model_validate(vendor).model_copy(update={"cover_image_url": _cover(vendor, storage)})


def vendor_owner(vendor: Vendor, storage: MediaStorage) -> VendorOwnerRead:
    return VendorOwnerRead.model_validate(vendor).model_copy(update={"cover_image_url": _cover(vendor, storage)})


def vendor_admin(vendor: Vendor, storage: MediaStorage) -> VendorAdminRead:
    return VendorAdminRead.model_validate(vendor).model_copy(
        update={
            "cover_image_url": _cover(vendor, storage),
            "has_pending_claim_code": vendor.claim_code_hash is not None and vendor.user_id is None,
        }
    )
