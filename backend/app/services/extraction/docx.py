import io
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from app.services.extraction.base import ExtractionError, Segment


def extract_docx(data: bytes) -> list[Segment]:
    """One segment per non-empty paragraph, with character offsets into the paragraphs
    joined by newlines (there is no single "original text" for a .docx, so this offset is
    relative to that joined reconstruction, not the source file's bytes)."""
    try:
        document = Document(io.BytesIO(data))
    except (PackageNotFoundError, KeyError, BadZipFile) as exc:
        raise ExtractionError(f"Could not read DOCX: {exc}") from exc

    segments: list[Segment] = []
    cursor = 0
    for paragraph in document.paragraphs:
        raw = paragraph.text
        text = raw.strip()
        if text:
            leading_ws = len(raw) - len(raw.lstrip())
            start = cursor + leading_ws
            segments.append(Segment(text=text, char_start=start, char_end=start + len(text)))
        cursor += len(raw) + 1  # +1 for the newline joining paragraphs
    return segments
