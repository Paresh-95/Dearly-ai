import subprocess
from pathlib import Path

import pytest

from app.domain.enums import SourceKind
from app.services.extraction.audio import extract_audio
from app.services.extraction.base import ExtractionError
from app.services.extraction.pipeline import extract
from app.services.extraction.video import extract_video
from app.services.providers.errors import ProviderNotConfigured
from app.services.providers.llm import FakeCandidateExtractor, get_candidate_extractor
from app.services.providers.stt import FakeSpeechTranscriber, get_speech_transcriber

FIXTURES = Path(__file__).parent / "fixtures"


class TestProviderNotConfiguredByDefault:
    """The test environment never sets MC_OPENAI_API_KEY, so these confirm the honest-
    failure path rather than a fabricated one."""

    def test_speech_transcriber_requires_configuration(self):
        get_speech_transcriber.cache_clear()
        with pytest.raises(ProviderNotConfigured):
            get_speech_transcriber()

    def test_candidate_extractor_requires_configuration(self):
        get_candidate_extractor.cache_clear()
        with pytest.raises(ProviderNotConfigured):
            get_candidate_extractor()


class TestFakeSpeechTranscriber:
    def test_transcribes_via_the_audio_extractor(self):
        segments = extract_audio(Path("/tmp/does-not-need-to-exist.wav"), FakeSpeechTranscriber())
        assert len(segments) == 1
        assert "fake transcript" in segments[0].text


class TestFakeCandidateExtractor:
    def test_skips_trivially_short_segments_and_never_invents_fields(self):
        from app.services.extraction.base import Segment

        segments = [Segment(text="hi"), Segment(text="Mum made poha every Sunday morning.")]
        candidates = FakeCandidateExtractor().extract(segments=segments, profile_context="Asha")
        assert len(candidates) == 1
        assert candidates[0].supporting_segment_ordinals == [2]
        assert candidates[0].description == segments[1].text


class TestPipelineDispatch:
    def test_text_kind_routes_to_the_text_extractor(self):
        segments, metadata = extract(SourceKind.TEXT, (FIXTURES / "sample.txt").read_bytes())
        assert metadata == {}
        assert segments[0].text == "Sunday breakfast"

    def test_audio_kind_requires_a_transcriber(self):
        # An assertion error is a programming-usage error, not a user-facing one: the worker
        # always resolves a transcriber before calling extract() for audio/video.
        with pytest.raises(AssertionError):
            extract(SourceKind.AUDIO, b"fake audio bytes")

    def test_video_extraction_fails_cleanly_without_ffmpeg(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", _raise_file_not_found)
        with pytest.raises(ExtractionError, match="ffmpeg"):
            extract_video(Path("/tmp/anything.mp4"), FakeSpeechTranscriber())


def _raise_file_not_found(*args, **kwargs):
    raise FileNotFoundError("no ffmpeg")
