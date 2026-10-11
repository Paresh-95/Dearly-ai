"""Memory-aware chunking (brief §4 step 5): a short memory stays intact as one chunk; a
longer one is split on sentence boundaries, never mid-sentence, with the title repeated on
every chunk so each one makes sense read on its own. Quotations are always kept whole —
never split across a chunk boundary — and attached to the chunk they end up in.

Deliberately a plain regex sentence splitter, not an NLP library: good enough for the chunk
sizes involved here, and Milestone 5's evaluation framework is where chunk-size/strategy
choices should actually be tuned against real retrieval metrics, not guessed at here."""

import re
from dataclasses import dataclass, field
from typing import Any

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


@dataclass
class ChunkDraft:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _split_sentences(text: str) -> list[str]:
    pieces: list[str] = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph:
            pieces.extend(s for s in _SENTENCE_BOUNDARY.split(paragraph) if s.strip())
    return pieces


def chunk_memory(
    *,
    title: str,
    description: str,
    quotations: list[str],
    category: str | None,
    date_text: str | None,
    location: str | None,
    people: list[str],
    max_chars: int,
) -> list[ChunkDraft]:
    metadata: dict[str, Any] = {
        "title": title,
        "category": category,
        "date_text": date_text,
        "location": location,
        "people": people,
    }
    quote_block = "\n".join(f'"{q}"' for q in quotations)

    full_text = title + "\n\n" + description
    if quote_block:
        full_text += "\n\nQuotations:\n" + quote_block

    if len(full_text) <= max_chars:
        return [ChunkDraft(text=full_text, metadata=metadata)]

    # Too long for one chunk: pack sentences greedily, each chunk prefixed with the title
    # for standalone context, never splitting a sentence (or a quotation, attached below).
    prefix = title + "\n\n"
    budget = max(max_chars - len(prefix), 200)

    chunks: list[str] = []
    current = ""
    for sentence in _split_sentences(description) or [""]:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > budget and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    chunks.append(current)

    if quote_block:
        chunks[-1] = f"{chunks[-1]}\n\nQuotations:\n{quote_block}"

    return [ChunkDraft(text=f"{prefix}{c}", metadata=metadata) for c in chunks]
