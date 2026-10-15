"""Synthetic test data builders. Never use real vendor or customer details here."""

from decimal import Decimal
from io import BytesIO
from uuid import uuid4

from PIL import Image
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.category import ServiceCategory
from app.models.enums import ApprovalStatus, UserRole
from app.models.user import User
from app.models.vendor import Vendor

DEFAULT_PASSWORD = "TestPass123"

# Hashing is deliberately slow (Argon2), so hash the default password once.
_DEFAULT_HASH = hash_password(DEFAULT_PASSWORD)


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def make_user(
    db: Session,
    *,
    role: UserRole = UserRole.CUSTOMER,
    email: str | None = None,
    password: str = DEFAULT_PASSWORD,
    full_name: str = "Test User",
    is_active: bool = True,
) -> User:
    user = User(
        full_name=full_name,
        email=(email or f"{unique(role.value)}@example.com").lower(),
        password_hash=_DEFAULT_HASH if password == DEFAULT_PASSWORD else hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def make_category(db: Session, name: str | None = None, *, is_active: bool = True) -> ServiceCategory:
    name = name or unique("Category")
    category = ServiceCategory(name=name, slug=name.lower().replace(" ", "-"), is_active=is_active)
    db.add(category)
    db.flush()
    return category


def make_vendor(
    db: Session,
    category: ServiceCategory,
    business_name: str | None = None,
    *,
    status: ApprovalStatus = ApprovalStatus.PENDING,
    owner: User | None = None,
    location: str = "Kamareddy",
    service_areas: list[str] | None = None,
    starting_price: Decimal | None = None,
    is_active: bool = True,
) -> Vendor:
    business_name = business_name or unique("Studio")
    vendor = Vendor(
        category_id=category.id,
        business_name=business_name,
        slug=unique(business_name.lower().replace(" ", "-")),
        contact_phone="+919000000000",
        location=location,
        service_areas=service_areas or [],
        starting_price=starting_price,
        approval_status=status,
        is_active=is_active,
        user_id=owner.id if owner else None,
    )
    db.add(vendor)
    db.flush()
    return vendor


def image_bytes(fmt: str = "PNG", size: tuple[int, int] = (24, 16), exif: Image.Exif | None = None) -> bytes:
    img = Image.new("RGB", size, (160, 30, 60))
    buffer = BytesIO()
    if exif is not None:
        img.save(buffer, fmt, exif=exif)
    else:
        img.save(buffer, fmt)
    return buffer.getvalue()
