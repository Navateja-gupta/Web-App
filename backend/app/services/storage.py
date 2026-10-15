"""Media storage abstraction.

Only LocalMediaStorage exists today. A cloud implementation (S3, GCS, Azure Blob)
can be added later with the same three methods without touching business logic.
"""

from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.core.config import settings


class MediaStorage(Protocol):
    def save(self, data: bytes, folder: str, extension: str) -> str:
        """Store bytes and return an opaque storage key."""

    def delete(self, key: str) -> None: ...

    def url(self, key: str) -> str:
        """Public URL for a stored key."""


class LocalMediaStorage:
    def __init__(self, root: Path, base_url: str) -> None:
        self.root = root.resolve()
        self.base_url = base_url.rstrip("/")

    def _path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        # Never read or write outside the media root.
        if self.root not in path.parents:
            raise ValueError("Invalid storage key")
        return path

    def save(self, data: bytes, folder: str, extension: str) -> str:
        # Server-generated name; the uploaded filename is never used.
        key = f"{folder.strip('/')}/{uuid4().hex}{extension}"
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def delete(self, key: str) -> None:
        self._path_for(key).unlink(missing_ok=True)

    def url(self, key: str) -> str:
        return f"{self.base_url}/{key}"


_storage = LocalMediaStorage(settings.MEDIA_ROOT, f"{settings.PUBLIC_BASE_URL}{settings.MEDIA_URL_PATH}")


def get_storage() -> MediaStorage:
    """FastAPI dependency (overridden in tests)."""
    return _storage
