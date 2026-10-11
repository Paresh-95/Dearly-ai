from pathlib import Path

from app.services.extraction.base import Segment
from app.services.providers.stt import SpeechTranscriber


def extract_audio(audio_path: Path, transcriber: SpeechTranscriber) -> list[Segment]:
    return transcriber.transcribe(audio_path)
