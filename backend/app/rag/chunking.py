# Every type except "story" is a short, discrete entry (a fact, a phrase, a
# single preference/routine/etc.) that should stay as one chunk regardless
# of length — only free-form narrative benefits from being split.
ATOMIC_TYPES = {
    "fact",
    "trait",
    "quote",
    "value",
    "routine",
    "preference",
    "physical_detail",
    "advice",
    "regret",
    "timeline_event",
}

_MAX_CHARS = 1200
_OVERLAP = 150


def chunk_memory(memory_type: str, raw_text: str) -> list[str]:
    """Short atomic memories stay as one chunk; long stories get split."""
    text = raw_text.strip()
    if not text:
        return []

    if memory_type in ATOMIC_TYPES or len(text) <= _MAX_CHARS:
        return [text]

    sentences = _split_sentences(text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > _MAX_CHARS and current:
            chunks.append(current.strip())
            current = current[-_OVERLAP:] + " " + sentence
        else:
            current = (current + " " + sentence).strip()
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _split_sentences(text: str) -> list[str]:
    import re

    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p for p in parts if p.strip()]
