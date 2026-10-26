import base64

import httpx

from app.core.config import settings

_LANGUAGE_CODES = {"en": "en-IN", "mr": "mr-IN"}
# Docs' own suggested bands: 1.0 default/conversational, 1.1-1.2 for
# notifications/news. True speed change (pitch-preserving), unlike the
# browser playbackRate hack used earlier — safe to push a bit further.
_PACE = 1.15

# Sarvam's own /text-to-speech reference documents `pitch` as bulbul:v2
# only (range -0.75 to 0.75); it isn't documented for /voices/clone at all.
# Empirically confirmed the field IS accepted there without error and
# produces non-identical audio across values — but TTS output is also
# non-deterministic run-to-run with identical params, so a real, reliable
# perceptual pitch effect on cloned voices isn't fully confirmed. Kept
# within the documented v2 range as a safe bound either way.
_MOOD_PITCH = {
    "warm": 0.15,
    "concerned": -0.15,
    "joyful": 0.45,
    "stern": -0.45,
    "scold": -0.65,
    "sad": -0.35,
    "excited": 0.6,
    "calm": 0.0,
    "neutral": 0.0,
}


class SarvamVoiceProvider:
    """Sarvam AI's voice cloning + TTS API, built specifically for Indian
    languages — evaluated as an alternative to Fish Audio for Marathi
    pronunciation accuracy (see app.llm.prompt_builder for the underlying
    issue: Fish Audio's model is Hindi-biased and mishandles Marathi-only
    sounds like the retroflex lateral "ळ").
    """

    def __init__(self) -> None:
        self._headers = {"api-subscription-key": settings.sarvam_api_key or ""}

    async def clone_voice(self, name: str, sample_bytes_list: list[bytes], language: str = "en") -> str:
        if not sample_bytes_list:
            raise ValueError("At least one reference sample is required")
        files = {"file": ("sample.wav", sample_bytes_list[0], "audio/wav")}
        data = {"name": name, "language": _LANGUAGE_CODES.get(language, "en-IN")}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.sarvam_base_url}/voices/create",
                headers=self._headers,
                data=data,
                files=files,
            )
            response.raise_for_status()
            return response.json()["data"]["voice_id"]

    async def synthesize(self, text: str, voice_id: str, language: str = "en", mood: str | None = None) -> bytes:
        data = {
            "voice_id": voice_id,
            "text": text,
            "language_code": _LANGUAGE_CODES.get(language, "en-IN"),
            "output_audio_codec": "mp3",
            "pace": _PACE,
            "pitch": _MOOD_PITCH.get(mood, 0.0) if mood else 0.0,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.sarvam_base_url}/voices/clone",
                headers=self._headers,
                data=data,
            )
            response.raise_for_status()
            audio_b64 = response.json()["audio_b64"]
            return base64.b64decode(audio_b64)
