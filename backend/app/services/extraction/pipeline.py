"""Dispatches a source's raw bytes to the right extractor. Pure plumbing — provider lookup
(and therefore `ProviderNotConfigured`) happens in the caller (the worker), not here, so this
function never has a hidden dependency on configuration."""

from pathlib import Path

from app.domain.enums import SourceKind
from app.services.extraction import docx as docx_extractor
from app.services.extraction import image as image_extractor
from app.services.extraction import pdf as pdf_extractor
from app.services.extraction import text as text_extractor
from app.services.extraction import video as video_extractor
from app.services.extraction import whatsapp as whatsapp_extractor
from app.services.extraction.audio import extract_audio
from app.services.extraction.base import ExtractionError, Segment
from app.services.providers.stt import SpeechTranscriber

NEEDS_TRANSCRIBER = {SourceKind.AUDIO, SourceKind.VIDEO}


def extract(
    kind: SourceKind,
    data: bytes,
    *,
    file_path: Path | None = None,
    transcriber: SpeechTranscriber | None = None,
) -> tuple[list[Segment], dict]:
    if kind == SourceKind.TEXT:
        return text_extractor.extract_text(data), {}
    if kind == SourceKind.PDF:
        return pdf_extractor.extract_pdf(data), {}
    if kind == SourceKind.DOCX:
        return docx_extractor.extract_docx(data), {}
    if kind == SourceKind.WHATSAPP:
        return whatsapp_extractor.extract_whatsapp(data), {}
    if kind == SourceKind.IMAGE:
        return image_extractor.extract_image(data)
    if kind == SourceKind.AUDIO:
        assert file_path is not None and transcriber is not None
        return extract_audio(file_path, transcriber), {}
    if kind == SourceKind.VIDEO:
        assert file_path is not None and transcriber is not None
        return video_extractor.extract_video(file_path, transcriber), {}
    raise ExtractionError(f"No extractor is implemented for source kind '{kind}'.")
