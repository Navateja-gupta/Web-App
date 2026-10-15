from collections.abc import Callable
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ApprovalStatus, UserRole
from app.services.storage import LocalMediaStorage
from tests.factories import image_bytes, make_category, make_user, make_vendor

API = settings.API_V1_PREFIX
ClientFor = Callable[..., TestClient]
URL = f"{API}/me/vendor/portfolio"


@pytest.fixture
def owner_client(client_for: ClientFor, db_session: Session) -> TestClient:
    owner = make_user(db_session, role=UserRole.VENDOR)
    make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED, owner=owner)
    return client_for(owner)


def upload(client: TestClient, data: bytes, filename: str = "photo.png", content_type: str = "image/png", **form: str):  # type: ignore[no-untyped-def]
    return client.post(URL, files={"file": (filename, data, content_type)}, data=form)


def stored_file(storage: LocalMediaStorage, url: str) -> bytes:
    key = url.removeprefix(storage.base_url + "/")
    return (storage.root / key).read_bytes()


def test_upload_valid_image(owner_client: TestClient, media_storage: LocalMediaStorage) -> None:
    response = upload(owner_client, image_bytes("PNG"), caption="Mandap decor")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["caption"] == "Mandap decor"
    assert body["url"].endswith(".png")
    Image.open(BytesIO(stored_file(media_storage, body["url"]))).verify()


def test_uploaded_filename_is_never_used(owner_client: TestClient) -> None:
    body = upload(owner_client, image_bytes("PNG"), filename="../../evil.php").json()
    assert "evil" not in body["url"] and ".php" not in body["url"] and ".." not in body["url"]


def test_exif_metadata_is_removed(owner_client: TestClient, media_storage: LocalMediaStorage) -> None:
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"  # Make
    original = image_bytes("JPEG", exif=exif)
    assert Image.open(BytesIO(original)).getexif().get(0x010F) == "SecretCameraMaker"

    body = upload(owner_client, original, filename="p.jpg", content_type="image/jpeg").json()
    cleaned = Image.open(BytesIO(stored_file(media_storage, body["url"])))
    assert len(cleaned.getexif()) == 0


def test_rejects_non_image_disguised_as_png(owner_client: TestClient) -> None:
    response = upload(owner_client, b"<?php system($_GET['c']); ?>", filename="x.png")
    assert response.status_code == 400


def test_rejects_disallowed_content_type(owner_client: TestClient) -> None:
    response = upload(owner_client, image_bytes("PNG"), filename="x.txt", content_type="text/plain")
    assert response.status_code == 400


def test_rejects_gif_even_if_labelled_png(owner_client: TestClient) -> None:
    assert upload(owner_client, image_bytes("GIF")).status_code == 400


def test_rejects_oversized_file(owner_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    big = image_bytes("PNG") + b"\0" * (1024 * 1024)
    response = upload(owner_client, big)
    assert response.status_code == 400
    assert "1 MB" in response.json()["detail"]


def test_portfolio_limit(owner_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MAX_PORTFOLIO_ITEMS", 1)
    assert upload(owner_client, image_bytes()).status_code == 201
    assert upload(owner_client, image_bytes()).status_code == 400


def test_delete_removes_file(owner_client: TestClient, media_storage: LocalMediaStorage) -> None:
    body = upload(owner_client, image_bytes()).json()
    path = media_storage.root / body["url"].removeprefix(media_storage.base_url + "/")
    assert path.exists()
    assert owner_client.delete(f"{URL}/{body['id']}").status_code == 204
    assert not path.exists()
    assert owner_client.get(URL).json() == []


def test_caption_and_order_update(owner_client: TestClient) -> None:
    first = upload(owner_client, image_bytes()).json()
    second = upload(owner_client, image_bytes()).json()
    owner_client.patch(f"{URL}/{second['id']}", json={"display_order": 0, "caption": "Cover"})
    owner_client.patch(f"{URL}/{first['id']}", json={"display_order": 5})
    items = owner_client.get(URL).json()
    assert [i["id"] for i in items] == [second["id"], first["id"]]
    assert items[0]["caption"] == "Cover"


def test_public_portfolio_and_cover_image(client_for: ClientFor, db_client: TestClient, db_session: Session) -> None:
    owner = make_user(db_session, role=UserRole.VENDOR)
    vendor = make_vendor(db_session, make_category(db_session), status=ApprovalStatus.APPROVED, owner=owner)
    body = upload(client_for(owner), image_bytes()).json()
    assert [p["id"] for p in db_client.get(f"{API}/vendors/{vendor.slug}/portfolio").json()] == [body["id"]]
    assert db_client.get(f"{API}/vendors/{vendor.slug}").json()["cover_image_url"] == body["url"]


def test_other_vendor_cannot_delete_photo(client_for: ClientFor, owner_client: TestClient, db_session: Session) -> None:
    photo_id = upload(owner_client, image_bytes()).json()["id"]
    other = make_user(db_session, role=UserRole.VENDOR)
    make_vendor(db_session, make_category(db_session), owner=other)
    assert client_for(other).delete(f"{URL}/{photo_id}").status_code == 404
