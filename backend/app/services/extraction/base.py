"""Shared extraction result type. Every extractor returns a list of these — the worker
writes them to `source_segments` unchanged, preserving exactly what was extracted (the
normalisation step, when one runs, writes to `normalized_text` and leaves `text` alone)."""

from dataclasses import dataclass


@dataclass
class Segment:
    text: str
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    t_start_ms: int | None = None
    t_end_ms: int | None = None
    speaker_label: str | None = None
    # True only when the speaker label came from explicit, structured metadata (e.g. a
    # WhatsApp export's "Sender:" prefix) rather than being inferred (e.g. audio diarisation).
    speaker_verified: bool = False


class ExtractionError(Exception):
    """Raised by an extractor for a genuine failure (corrupt file, unsupported encoding,
    required provider not configured). The worker records this as the job's error and marks
    it failed — never silently swallowed."""
