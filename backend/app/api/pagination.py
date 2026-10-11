"""Opaque cursor pagination: base64("<created_at-iso>|<id>"), compared as a tuple so page
boundaries are stable even when several rows share a `created_at` value."""

import base64
import binascii
from datetime import datetime
from uuid import UUID

from app.core.errors import AppError


class InvalidCursor(AppError):
    status_code = 422
    code = "invalid_cursor"


def encode_cursor(created_at: datetime, id_: UUID) -> str:
    raw = f"{created_at.isoformat()}|{id_}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_str, id_str = raw.split("|", 1)
        return datetime.fromisoformat(ts_str), UUID(id_str)
    except (ValueError, binascii.Error) as exc:
        raise InvalidCursor("Invalid pagination cursor") from exc
