from app.services.extraction.base import ExtractionError, Segment


def extract_text(data: bytes) -> list[Segment]:
    """Plain text, split into paragraphs (blank-line separated) with character offsets into
    the original decoded text. Offsets are computed arithmetically (not by searching for the
    block's text) so repeated paragraphs can't be mismatched to the wrong occurrence."""
    try:
        raw = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionError(f"Could not decode file as UTF-8 text: {exc}") from exc

    segments: list[Segment] = []
    cursor = 0
    for block in raw.split("\n\n"):
        block_start = cursor
        cursor = block_start + len(block) + 2  # +2 for the "\n\n" separator consumed by split
        stripped = block.strip()
        if not stripped:
            continue
        leading_ws = len(block) - len(block.lstrip())
        start = block_start + leading_ws
        segments.append(Segment(text=stripped, char_start=start, char_end=start + len(stripped)))
    return segments
