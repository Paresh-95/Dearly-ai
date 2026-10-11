"""Image handling: EXIF metadata always; OCR text only best-effort.

A plain photograph has no OCR-able text — that is the normal case, not a failure. Unlike
audio/video/LLM extraction, a missing OCR engine never fails the ingestion job; it just means
no text segment is produced, same as a photo that genuinely has no text in it. GPS/location
EXIF tags are deliberately not read: a parent's photo location is exactly the kind of detail
the brief asks us not to infer without the user confirming it."""

import io
import logging

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS

from app.core.config import get_settings
from app.services.extraction.base import ExtractionError, Segment

log = logging.getLogger("app.extraction.image")

_METADATA_TAGS = {"DateTime", "DateTimeOriginal", "Make", "Model", "Orientation"}


def _read_exif(image: Image.Image) -> dict[str, str]:
    raw = image.getexif()
    out: dict[str, str] = {}
    for tag_id, value in raw.items():
        name = TAGS.get(tag_id)
        if name in _METADATA_TAGS:
            out[name] = str(value)
    return out


def extract_image(data: bytes) -> tuple[list[Segment], dict[str, str | int]]:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except UnidentifiedImageError as exc:
        raise ExtractionError(f"Could not read image: {exc}") from exc

    metadata: dict[str, str | int] = {
        "width": image.width,
        "height": image.height,
        "format": image.format or "unknown",
        **_read_exif(image),
    }

    try:
        import pytesseract

        text = pytesseract.image_to_string(image, lang=get_settings().ocr_languages).strip()
    except Exception as exc:  # pytesseract missing, tesseract binary missing, or a decode error
        log.info("OCR unavailable or failed, continuing without it: %s", exc)
        metadata["ocr_attempted"] = True
        metadata["ocr_available"] = False
        return [], metadata

    metadata["ocr_attempted"] = True
    metadata["ocr_available"] = True
    return ([Segment(text=text)] if text else []), metadata
