import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.extraction.base import ExtractionError, Segment


def extract_pdf(data: bytes) -> list[Segment]:
    """One segment per non-empty page, with the 1-indexed page number as provenance."""
    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise ExtractionError(f"Could not read PDF: {exc}") from exc

    segments: list[Segment] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            segments.append(Segment(text=text, page=i))
    return segments
