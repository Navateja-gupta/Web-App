import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute


def collapse_spaces(value: str) -> str:
    return " ".join(value.split())


def slugify(text: str, max_length: int = 80) -> str:
    """ASCII URL slug. Non-Latin names (e.g. Telugu) produce an empty string."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")[:max_length].rstrip("-")


def unique_slug(db: Session, column: InstrumentedAttribute[str], text: str, fallback: str) -> str:
    """Return a slug for `text` that is not yet used in `column` (adds -2, -3, ...)."""
    base = slugify(text) or fallback
    candidate, n = base, 2
    while db.scalar(select(column).where(column == candidate)):
        candidate = f"{base}-{n}"
        n += 1
    return candidate
