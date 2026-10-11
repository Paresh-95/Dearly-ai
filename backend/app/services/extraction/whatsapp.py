import re

from app.services.extraction.base import ExtractionError, Segment

# WhatsApp's "Export chat" .txt format. Covers the two common date/time stamp styles:
#   12/04/23, 9:05 AM - Asha: Good morning!
#   12/04/2023, 09:05 - Asha: Good morning!
# A message that spans multiple lines (no new timestamp prefix) is appended to the segment
# started by the line before it.
_MESSAGE_RE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?:\s?[AaPp][Mm])?)\s*-\s*([^:]+):\s(.*)$"
)
# System notices ("Messages and calls are end-to-end encrypted", "X added Y") share the
# timestamp prefix but have no "sender:" — skip them, they are not memories.
_SYSTEM_RE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?:\s?[AaPp][Mm])?)\s*-\s*(.*)$"
)


def extract_whatsapp(data: bytes) -> list[Segment]:
    """One segment per message. `speaker_label` is the sender name exactly as WhatsApp wrote
    it — that is explicit, structured metadata from the export, not an inference, so
    `speaker_verified=True` (unlike audio diarisation, which never sets it)."""
    try:
        raw = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ExtractionError(f"Could not decode WhatsApp export as UTF-8: {exc}") from exc

    segments: list[Segment] = []
    current: Segment | None = None
    for line in raw.splitlines():
        line = line.strip("‎‏").rstrip()
        if not line:
            continue
        match = _MESSAGE_RE.match(line)
        if match:
            _, _, sender, text = match.groups()
            current = Segment(text=text, speaker_label=sender.strip(), speaker_verified=True)
            segments.append(current)
        elif _SYSTEM_RE.match(line):
            current = None  # a system notice; any continuation line is dropped with it
        elif current is not None:
            current.text += "\n" + line

    if not segments:
        raise ExtractionError(
            "No WhatsApp-formatted messages were found in this file. "
            "Make sure it is an unedited 'Export chat' .txt file."
        )
    return segments
