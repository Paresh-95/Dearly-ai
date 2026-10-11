"""Speech-to-text for audio sources (and for video, after ffmpeg pulls out the audio track).
See docs/decisions/0003-provider-fallbacks.md for why this fails the job cleanly rather than
fabricating a transcript when no provider is configured."""

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from openai import OpenAI

from app.core.config import get_settings
from app.services.extraction.base import Segment
from app.services.providers.errors import ProviderNotConfigured


class SpeechTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path) -> list[Segment]: ...


class OpenAISpeechTranscriber(SpeechTranscriber):
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def transcribe(self, audio_path: Path) -> list[Segment]:
        with audio_path.open("rb") as f:
            result = self._client.audio.transcriptions.create(
                file=f,
                model=self._model,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        segments = getattr(result, "segments", None) or []
        if not segments:
            # Some OpenAI-compatible backends ignore timestamp_granularities and return only
            # the full text; still better than discarding the transcript entirely.
            text = getattr(result, "text", "").strip()
            return [Segment(text=text)] if text else []
        return [
            Segment(
                text=seg.text.strip(),
                t_start_ms=round(seg.start * 1000),
                t_end_ms=round(seg.end * 1000),
                # Whisper-style transcription does not diarise, so there is no speaker label
                # to attach, verified or otherwise.
            )
            for seg in segments
            if seg.text.strip()
        ]


class FakeSpeechTranscriber(SpeechTranscriber):
    """Deterministic test double — never selected by configuration."""

    def transcribe(self, audio_path: Path) -> list[Segment]:
        text = f"[fake transcript of {audio_path.name}]"
        return [Segment(text=text, t_start_ms=0, t_end_ms=1000)]


@lru_cache
def get_speech_transcriber() -> SpeechTranscriber:
    s = get_settings()
    if not s.openai_api_key:
        raise ProviderNotConfigured(
            "No speech-to-text provider is configured (MC_OPENAI_API_KEY is unset), "
            "so this recording cannot be transcribed."
        )
    return OpenAISpeechTranscriber(
        api_key=s.openai_api_key, base_url=s.openai_base_url, model=s.openai_stt_model
    )
