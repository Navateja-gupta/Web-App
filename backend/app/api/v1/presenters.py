"""Convert ORM objects into response schemas that need extra context (e.g. media URLs, ratings)."""

from sqlalchemy.orm import Session

from app.models.vendor import Vendor, VendorPortfolio
from app.schemas.portfolio import PortfolioRead
from app.schemas.vendor import VendorAdminRead, VendorOwnerRead, VendorPublic
from app.services.reviews import review_stats
from app.services.storage import MediaStorage

RatingStats = dict[int, tuple[float, int]]


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


def _extras(vendor: Vendor, storage: MediaStorage, stats: RatingStats | None) -> dict[str, object]:
    average, count = (stats or {}).get(vendor.id, (None, 0))
    return {"cover_image_url": _cover(vendor, storage), "rating_average": average, "review_count": count}


def vendor_public(vendor: Vendor, storage: MediaStorage, stats: RatingStats | None = None) -> VendorPublic:
    return VendorPublic.model_validate(vendor).model_copy(update=_extras(vendor, storage, stats))


def vendors_public(db: Session, vendors: list[Vendor], storage: MediaStorage) -> list[VendorPublic]:
    """Many vendors at once, with ratings loaded in a single query."""
    stats = review_stats(db, [v.id for v in vendors])
    return [vendor_public(v, storage, stats) for v in vendors]


def vendor_owner(vendor: Vendor, storage: MediaStorage, stats: RatingStats | None = None) -> VendorOwnerRead:
    return VendorOwnerRead.model_validate(vendor).model_copy(update=_extras(vendor, storage, stats))


def vendor_admin(vendor: Vendor, storage: MediaStorage, stats: RatingStats | None = None) -> VendorAdminRead:
    update = _extras(vendor, storage, stats)
    update["has_pending_claim_code"] = vendor.claim_code_hash is not None and vendor.user_id is None
    return VendorAdminRead.model_validate(vendor).model_copy(update=update)
