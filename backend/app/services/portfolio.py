from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BusinessRuleError, NotFoundError
from app.models.enums import MediaType
from app.models.user import User
from app.models.vendor import Vendor, VendorPortfolio
from app.schemas.portfolio import PortfolioUpdate
from app.services.audit import record_audit
from app.services.images import process_image
from app.services.storage import MediaStorage


def list_portfolio(db: Session, vendor: Vendor) -> list[VendorPortfolio]:
    return list(
        db.scalars(
            select(VendorPortfolio)
            .where(VendorPortfolio.vendor_id == vendor.id)
            .order_by(VendorPortfolio.display_order, VendorPortfolio.id)
        )
    )


def get_portfolio_item(db: Session, vendor: Vendor, item_id: int) -> VendorPortfolio:
    item = db.scalar(
        select(VendorPortfolio).where(VendorPortfolio.id == item_id, VendorPortfolio.vendor_id == vendor.id)
    )
    if item is None:
        raise NotFoundError("Photo not found")
    return item


def add_image(
    db: Session, storage: MediaStorage, vendor: Vendor, data: bytes, caption: str | None, actor: User
) -> VendorPortfolio:
    count = db.scalar(select(func.count()).where(VendorPortfolio.vendor_id == vendor.id)) or 0
    if count >= settings.MAX_PORTFOLIO_ITEMS:
        raise BusinessRuleError(f"A vendor can have at most {settings.MAX_PORTFOLIO_ITEMS} photos")

    image_bytes, extension = process_image(data)
    key = storage.save(image_bytes, f"portfolio/{vendor.id}", extension)
    try:
        next_order = (
            db.scalar(select(func.max(VendorPortfolio.display_order)).where(VendorPortfolio.vendor_id == vendor.id))
            or 0
        ) + 1
        item = VendorPortfolio(
            vendor_id=vendor.id,
            media_path=key,
            media_type=MediaType.IMAGE,
            caption=(caption or "").strip()[:255] or None,
            display_order=next_order if count else 0,
        )
        db.add(item)
        db.flush()
        record_audit(db, actor_id=actor.id, action="portfolio.added", entity_type="portfolio", entity_id=item.id,
                     details={"vendor_id": vendor.id})
        db.commit()
    except Exception:
        # Keep disk and database consistent if the database step fails.
        storage.delete(key)
        raise
    return item


def update_item(db: Session, vendor: Vendor, item_id: int, data: PortfolioUpdate) -> VendorPortfolio:
    item = get_portfolio_item(db, vendor, item_id)
    changes = data.model_dump(exclude_unset=True)
    if "caption" in changes:
        item.caption = changes["caption"]
    if changes.get("display_order") is not None:
        item.display_order = changes["display_order"]
    db.commit()
    return item


def delete_item(db: Session, storage: MediaStorage, vendor: Vendor, item_id: int, actor: User) -> None:
    item = get_portfolio_item(db, vendor, item_id)
    key = item.media_path
    record_audit(db, actor_id=actor.id, action="portfolio.deleted", entity_type="portfolio", entity_id=item.id,
                 details={"vendor_id": vendor.id})
    db.delete(item)
    db.commit()
    storage.delete(key)
