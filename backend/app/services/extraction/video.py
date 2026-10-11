import subprocess
import tempfile
from pathlib import Path

from app.services.extraction.audio import extract_audio
from app.services.extraction.base import ExtractionError, Segment
from app.services.providers.stt import SpeechTranscriber


def extract_video(video_path: Path, transcriber: SpeechTranscriber) -> list[Segment]:
    """Pulls the audio track out with ffmpeg, then transcribes it exactly like a plain
    audio upload. Timestamps come back relative to the video, which is what matters for a
    "timestamped transcript segment" — we never attempt speaker identification from the
    picture or the voice."""
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(video_path),
                    "-vn", "-ac", "1", "-ar", "16000", tmp.name,
                ],
                check=True,
                capture_output=True,
                timeout=600,
            )
        except FileNotFoundError as exc:
            raise ExtractionError(
                "ffmpeg is not installed on this server; video cannot be processed."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="replace")[-500:] if exc.stderr else ""
            raise ExtractionError(f"Could not extract audio from this video: {stderr}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ExtractionError("Extracting audio from this video took too long.") from exc

        return extract_audio(Path(tmp.name), transcriber)
