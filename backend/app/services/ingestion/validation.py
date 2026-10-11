import magic

from app.core.errors import AppError
from app.domain.enums import SourceKind


class UnsupportedFileType(AppError):
    status_code = 415
    code = "unsupported_media"


class FileTooLarge(AppError):
    status_code = 413
    code = "too_large"


# What a file actually is, sniffed by libmagic, must start with one of these for the kind
# the user picked. We never trust the client-supplied Content-Type header alone — it's
# trivial to spoof and would otherwise let a mislabelled file reach the wrong extractor.
_ALLOWED_PREFIXES: dict[SourceKind, tuple[str, ...]] = {
    SourceKind.TEXT: ("text/",),
    SourceKind.WHATSAPP: ("text/",),
    SourceKind.PDF: ("application/pdf",),
    # A .docx is a zip container; some libmagic databases identify it precisely, others
    # only as a generic zip. The WhatsApp-style "does this actually parse" check is what
    # really validates a .docx, same as for WhatsApp exports.
    SourceKind.DOCX: ("application/vnd.openxmlformats-officedocument", "application/zip"),
    SourceKind.IMAGE: ("image/",),
    SourceKind.AUDIO: ("audio/",),
    SourceKind.VIDEO: ("video/",),
}


def detect_and_validate(kind: SourceKind, data: bytes) -> str:
    """Returns the sniffed MIME type, or raises `UnsupportedFileType` if it doesn't match
    the declared kind."""
    detected = magic.from_buffer(data, mime=True)
    if not any(detected.startswith(p) for p in _ALLOWED_PREFIXES.get(kind, ())):
        raise UnsupportedFileType(
            f"This file looks like '{detected}', which isn't a supported "
            f"{kind.value.replace('_', ' ')} file."
        )
    return detected
