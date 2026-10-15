"""Validate and re-encode uploaded images.

Re-encoding means the stored file is always a clean image produced by Pillow:
anything hidden in the original (scripts, polyglot payloads, EXIF/GPS metadata)
is dropped. The file type is decided by decoding the content, not by the filename
or the Content-Type header.
"""

import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import BusinessRuleError

ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
MAX_DIMENSION = 2560
MAX_PIXELS = 40_000_000  # guards against decompression bombs

INVALID_IMAGE = "Upload a valid JPEG, PNG or WebP image."


def process_image(data: bytes) -> tuple[bytes, str]:
    """Return (re-encoded bytes, file extension) or raise BusinessRuleError."""
    if not data:
        raise BusinessRuleError("The uploaded file is empty.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as probe:
                if probe.format not in ALLOWED_FORMATS:
                    raise BusinessRuleError(INVALID_IMAGE)
                if probe.width * probe.height > MAX_PIXELS:
                    raise BusinessRuleError("Image dimensions are too large.")
                probe.verify()

            with Image.open(BytesIO(data)) as img:
                image_format = img.format or ""
                img.load()
                img = ImageOps.exif_transpose(img)  # respect phone rotation before metadata is dropped
                img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

                out = BytesIO()
                if image_format == "JPEG":
                    img.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
                elif image_format == "PNG":
                    img.save(out, "PNG", optimize=True)
                else:
                    img.save(out, "WEBP", quality=85)
    except BusinessRuleError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, SyntaxError, ValueError):
        raise BusinessRuleError(INVALID_IMAGE)

    return out.getvalue(), ALLOWED_FORMATS[image_format]
