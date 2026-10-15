from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.dependencies.pagination import PageParams
from app.models.booking import Booking, Review
from app.models.enums import BookingStatus
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.review import ReviewCreate
from app.services.audit import record_audit


def reviewer_name(user: User) -> str:
    """'Ravi Kumar' -> 'Ravi K.' so reviews never expose full customer names."""
    parts = user.full_name.split()
    if not parts:
        return "Customer"
    return f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else parts[0]


def review_stats(db: Session, vendor_ids: list[int]) -> dict[int, tuple[float, int]]:
    """{vendor_id: (average rating, count)} over visible reviews only."""
    if not vendor_ids:
        return {}
    rows = db.execute(
        select(Review.vendor_id, func.avg(Review.rating), func.count())
        .where(Review.vendor_id.in_(vendor_ids), Review.is_visible.is_(True))
        .group_by(Review.vendor_id)
    ).all()
    return {vendor_id: (round(float(avg), 1), count) for vendor_id, avg, count in rows}


def create_review(db: Session, customer: User, booking_id: int, data: ReviewCreate) -> Review:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id, Booking.customer_id == customer.id))
    if booking is None:
        raise NotFoundError("Booking not found")
    if booking.booking_status != BookingStatus.COMPLETED:
        raise BusinessRuleError("You can review a vendor only after the booking is completed")
    if db.scalar(select(Review.id).where(Review.booking_id == booking.id)):
        raise ConflictError("You have already reviewed this booking")

    review = Review(
        customer_id=customer.id, vendor_id=booking.vendor_id, booking_id=booking.id,
        rating=data.rating, comment=data.comment,
    )
    db.add(review)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("You have already reviewed this booking")
    record_audit(db, actor_id=customer.id, action="review.created", entity_type="review", entity_id=review.id,
                 details={"vendor_id": booking.vendor_id, "rating": data.rating})
    db.commit()
    return review


def list_public_reviews(db: Session, vendor: Vendor, params: PageParams) -> tuple[list[Review], int]:
    stmt = select(Review).where(Review.vendor_id == vendor.id, Review.is_visible.is_(True))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.options(selectinload(Review.customer))
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(params.offset)
        .limit(params.size)
    ).all()
    return list(items), total


def list_admin_reviews(
    db: Session, params: PageParams, *, vendor_id: int | None = None, is_visible: bool | None = None
) -> tuple[list[Review], int]:
    stmt = select(Review)
    if vendor_id is not None:
        stmt = stmt.where(Review.vendor_id == vendor_id)
    if is_visible is not None:
        stmt = stmt.where(Review.is_visible.is_(is_visible))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.options(selectinload(Review.customer), selectinload(Review.vendor).selectinload(Vendor.category))
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(params.offset)
        .limit(params.size)
    ).all()
    return list(items), total


def set_visibility(db: Session, admin: User, review_id: int, is_visible: bool) -> Review:
    review = db.scalar(
        select(Review)
        .where(Review.id == review_id)
        .options(selectinload(Review.customer), selectinload(Review.vendor).selectinload(Vendor.category))
    )
    if review is None:
        raise NotFoundError("Review not found")
    review.is_visible = is_visible
    record_audit(db, actor_id=admin.id, action="review.shown" if is_visible else "review.hidden",
                 entity_type="review", entity_id=review.id)
    db.commit()
    return review
