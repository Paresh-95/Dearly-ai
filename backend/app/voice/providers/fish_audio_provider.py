import httpx

from app.core.config import settings


class FishAudioVoiceProvider:
    """Cloning goes through Fish Audio's own native API (OpenRouter has no
    cloning endpoint); synthesis goes through OpenRouter's speech route for
    the free `fish-audio/s2.1-pro-free:free` model, passing the cloned voice
    id. The `:free` suffix is required — without it OpenRouter 404s, since
    that resolves to a different (non-existent) model slug.
    """

    def __init__(self) -> None:
        self._fish_headers = {"Authorization": f"Bearer {settings.fish_audio_api_key}"}
        self._openrouter_headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "AI Memorial Persona (MVP)",
        }

    async def clone_voice(self, name: str, sample_bytes_list: list[bytes]) -> str:
        files = [("voices", (f"sample_{i}.mp3", data, "audio/mpeg")) for i, data in enumerate(sample_bytes_list)]
        data = {"type": "tts", "title": name, "train_mode": "fast", "visibility": "private"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.fish_audio_base_url}/model",
                headers=self._fish_headers,
                data=data,
                files=files,
            )
            response.raise_for_status()
            return response.json()["_id"]

    async def synthesize(self, text: str, voice_id: str, language: str = "en", mood: str | None = None) -> bytes:
        # OpenRouter's route doesn't support a meaningful language override
        # (confirmed: the `language` field only affects normalization/
        # timestamps, not accent) — kept for interface parity with other
        # providers (e.g. Sarvam) that do use it.
        #
        # Fish Audio's S2/S2.1 models read emotion/delivery cues as a
        # natural-language `[bracket]` tag at the start of the text, not a
        # separate API field — confirmed via docs.fish.audio's emotion
        # reference (S1 uses a fixed tag set; S2+ accepts free-form
        # descriptive words in brackets).
        if mood:
            text = f"[{mood}] {text}"

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.tts_base_url}/audio/speech",
                headers=self._openrouter_headers,
                json={
                    "model": settings.tts_model,
                    "input": text,
                    "voice": voice_id,
                    "response_format": "mp3",
                },
            )
            response.raise_for_status()
            return response.content
