"""Add or remove clearly-labelled DEMO vendors for trying out the marketplace.

Every demo vendor:
  * has a business name starting with "[Demo]" and a slug starting with "demo-"
  * says "Demo listing" in its description
  * uses example.com emails and placeholder photos stamped "DEMO PHOTO"

Run from backend/ with the virtual environment active:

    python -m app.scripts.seed_demo            # add demo vendors (safe to run twice)
    python -m app.scripts.seed_demo --remove   # remove them again

Demo vendors that already have enquiries or bookings are deactivated instead of deleted,
so no customer history is lost.
"""

import argparse
import sys
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.booking import Booking
from app.models.category import ServiceCategory
from app.models.enums import AvailabilityStatus, PricingType, UserRole
from app.models.quotation import QuotationRequest
from app.models.user import User
from app.models.vendor import Vendor, VendorPortfolio
from app.schemas.package import PackageCreate
from app.schemas.portfolio import AvailabilitySet
from app.schemas.vendor import VendorCreate
from app.services import availability as availability_service
from app.services import packages as package_service
from app.services import portfolio as portfolio_service
from app.services import vendors as vendor_service
from app.services.audit import record_audit
from app.services.storage import get_storage

DEMO_NOTE = "Demo listing for testing the platform. This is not a real business."

# category slug -> list of demo vendors
DEMO_VENDORS: dict[str, list[dict]] = {
    "photography": [
        {
            "name": "Golden Frame Studio", "location": "Kamareddy", "areas": ["Kamareddy", "Yellareddy", "Domakonda"],
            "price": "35000", "colour": (120, 30, 50),
            "about": "Candid and traditional wedding photography with same-week album design.",
            "packages": [
                ("Silver", PricingType.FIXED, "35000", None, ["1 photographer", "300 edited photos", "Online gallery"], ["Printed album"]),
                ("Gold", PricingType.FIXED, "65000", None, ["2 photographers", "Candid + traditional", "40-page album"], ["Drone"]),
                ("Drone coverage add-on", PricingType.FIXED, "12000", None, ["Aerial shots on wedding day"], []),
            ],
        },
        {
            "name": "Moments by Ravi", "location": "Nizamabad", "areas": ["Nizamabad", "Kamareddy", "Bodhan"],
            "price": "25000", "colour": (40, 70, 120),
            "about": "Natural-light candid photography and short highlight films.",
            "packages": [
                ("Candid only", PricingType.STARTING_FROM, "25000", "40000", ["Full-day candid coverage"], ["Video"]),
                ("Photo + highlight film", PricingType.QUOTE_ON_REQUEST, None, None, ["Photo", "3-minute film"], []),
            ],
        },
    ],
    "event-decorators": [
        {
            "name": "Marigold Mandap Decor", "location": "Kamareddy", "areas": ["Kamareddy", "Banswada", "Bhiknoor"],
            "price": "45000", "colour": (200, 120, 20),
            "about": "Traditional mandap, stage and flower decoration for weddings and receptions.",
            "packages": [
                ("Simple stage", PricingType.FIXED, "45000", None, ["Stage backdrop", "Fresh flower garlands"], ["Lighting"]),
                ("Grand mandap", PricingType.STARTING_FROM, "120000", "200000", ["Mandap", "Entrance arch", "Lighting"], []),
            ],
        },
        {
            "name": "Shubh Events & Lighting", "location": "Yellareddy", "areas": ["Yellareddy", "Kamareddy"],
            "price": None, "colour": (90, 40, 110),
            "about": "Lighting, entrance and haldi/mehendi theme decoration.",
            "packages": [
                ("Haldi theme decor", PricingType.QUOTE_ON_REQUEST, None, None, ["Yellow theme", "Seating area"], []),
            ],
        },
    ],
    "catering": [
        {
            "name": "Annapurna Caterers", "location": "Kamareddy", "areas": ["Kamareddy", "Domakonda", "Bhiknoor"],
            "price": "280", "colour": (30, 110, 60),
            "about": "Traditional Telangana vegetarian and non-vegetarian wedding meals.",
            "packages": [
                ("Veg meals", PricingType.PER_PERSON, "280", None, ["2 curries", "Dal", "Rice", "Sweet", "Curd"], ["Service staff tips"]),
                ("Non-veg meals", PricingType.PER_PERSON, "420", None, ["Chicken curry", "Biryani", "Sweet"], []),
            ],
        },
        {
            "name": "Royal Biryani Kitchen", "location": "Nizamabad", "areas": ["Nizamabad", "Kamareddy"],
            "price": "350", "colour": (150, 60, 20),
            "about": "Dum biryani and full reception buffets.",
            "packages": [
                ("Biryani buffet", PricingType.PER_PERSON, "350", "450", ["Chicken/mutton dum biryani", "Raita", "Double ka meetha"], []),
            ],
        },
    ],
    "dj": [
        {
            "name": "DJ Beats Kamareddy", "location": "Kamareddy", "areas": ["Kamareddy", "Yellareddy", "Banswada"],
            "price": "15000", "colour": (20, 20, 60),
            "about": "DJ with sound and lighting for sangeet, baraat and reception.",
            "packages": [
                ("Sangeet night", PricingType.FIXED, "15000", None, ["4 hours", "Sound system", "Basic lights"], ["Generator"]),
                ("Baraat + reception", PricingType.FIXED, "28000", None, ["Baraat DJ vehicle", "Reception DJ"], []),
            ],
        },
        {
            "name": "Sound Wave Events", "location": "Banswada", "areas": ["Banswada", "Kamareddy", "Bodhan"],
            "price": "12000", "colour": (0, 90, 110),
            "about": "Budget-friendly DJ and dhol for small functions.",
            "packages": [
                ("DJ + dhol", PricingType.STARTING_FROM, "12000", "20000", ["DJ", "2 dhol players"], []),
            ],
        },
    ],
}


def slugify_demo(name: str) -> str:
    return "demo-" + "-".join(name.lower().replace("&", "and").split())


def demo_photo(title: str, caption: str, colour: tuple[int, int, int]) -> bytes:
    """A plain coloured image clearly stamped as a demo, never mistaken for real work."""
    # 4:3 matches the vendor cards, and text stays away from the edges so it is never cropped.
    width, height = 1200, 900
    img = Image.new("RGB", (width, height), colour)
    draw = ImageDraw.Draw(img)
    for i in range(0, height, 8):  # simple vertical shading
        shade = tuple(min(255, c + i // 20) for c in colour)
        draw.line([(0, i), (width, i)], fill=shade)
    big = ImageFont.load_default(size=96)
    small = ImageFont.load_default(size=44)

    def centred(y: int, text: str, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> None:
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        draw.text(((width - (right - left)) / 2, y), text, fill=fill, font=font)

    centred(330, "DEMO PHOTO", big, (255, 255, 255))
    centred(470, title, small, (255, 255, 255))
    centred(540, caption, small, (230, 230, 230))
    out = BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()


def add_demo_vendors() -> None:
    storage = get_storage()
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True)).order_by(User.id))
        if admin is None:
            sys.exit("No active administrator found. Create one first with app.scripts.create_admin.")

        phone_counter = 1
        created = 0
        for category_slug, vendors in DEMO_VENDORS.items():
            category = db.scalar(select(ServiceCategory).where(ServiceCategory.slug == category_slug))
            if category is None or not category.is_active:
                print(f"  skipped category '{category_slug}' (not found or inactive)")
                continue
            for spec in vendors:
                name = f"[Demo] {spec['name']}"
                phone = f"+9190000000{phone_counter:02d}"
                phone_counter += 1
                if db.scalar(select(Vendor.id).where(Vendor.slug == slugify_demo(spec["name"]))):
                    print(f"  exists: {name}")
                    continue

                vendor = vendor_service.create_vendor(
                    db,
                    VendorCreate(
                        business_name=name,
                        category_id=category.id,
                        description=f"{spec['about']}\n\n{DEMO_NOTE}",
                        contact_phone=phone,
                        contact_email=f"{slugify_demo(spec['name'])}@example.com",
                        location=spec["location"],
                        service_areas=spec["areas"],
                        starting_price=Decimal(spec["price"]) if spec["price"] else None,
                    ),
                    owner=None,
                    actor=admin,
                )
                # Predictable slug so --remove can find demo vendors reliably.
                vendor.slug = slugify_demo(spec["name"])
                db.commit()

                for pkg_name, pricing, price, price_max, inc, exc in spec["packages"]:
                    package_service.create_package(
                        db, vendor,
                        PackageCreate(name=pkg_name, pricing_type=pricing, price=price, price_max=price_max,
                                      inclusions=inc, exclusions=exc, description=DEMO_NOTE),
                        admin,
                    )
                for caption in ("Sample work 1", "Sample work 2"):
                    portfolio_service.add_image(
                        db, storage, vendor, demo_photo(name, caption, spec["colour"]), f"Demo photo · {caption}", admin
                    )
                for offset, status in ((10, AvailabilityStatus.AVAILABLE), (17, AvailabilityStatus.BOOKED), (24, AvailabilityStatus.AVAILABLE)):
                    availability_service.set_availability(
                        db, vendor, date.today() + timedelta(days=offset),
                        AvailabilitySet(availability_status=status, notes="Demo data"),
                    )
                vendor_service.change_approval(db, vendor_service.get_vendor(db, vendor.id), "approve", admin, None)
                created += 1
                print(f"  added: {name} ({category.name})")
        print(f"Done. {created} demo vendor(s) added.")


def remove_demo_vendors() -> None:
    storage = get_storage()
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id))
        vendors = db.scalars(select(Vendor).where(Vendor.slug.startswith("demo-"), Vendor.business_name.startswith("[Demo]"))).all()
        for vendor in vendors:
            has_history = db.scalar(select(QuotationRequest.id).where(QuotationRequest.vendor_id == vendor.id).limit(1)) or db.scalar(
                select(Booking.id).where(Booking.vendor_id == vendor.id).limit(1)
            )
            if has_history:
                vendor.is_active = False
                record_audit(db, actor_id=admin.id if admin else None, action="vendor.demo_deactivated",
                             entity_type="vendor", entity_id=vendor.id)
                db.commit()
                print(f"  deactivated (has enquiries/bookings): {vendor.business_name}")
                continue
            keys = list(db.scalars(select(VendorPortfolio.media_path).where(VendorPortfolio.vendor_id == vendor.id)))
            record_audit(db, actor_id=admin.id if admin else None, action="vendor.demo_removed",
                         entity_type="vendor", entity_id=vendor.id, details={"name": vendor.business_name})
            # Database-level delete so packages, photos, availability and shortlists cascade.
            db.execute(delete(Vendor).where(Vendor.id == vendor.id))
            db.commit()
            for key in keys:
                storage.delete(key)
            print(f"  removed: {vendor.business_name}")
        print(f"Done. {len(vendors)} demo vendor(s) processed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add or remove demo vendors.")
    parser.add_argument("--remove", action="store_true", help="Remove all demo vendors")
    args = parser.parse_args()
    remove_demo_vendors() if args.remove else add_demo_vendors()


if __name__ == "__main__":
    main()
