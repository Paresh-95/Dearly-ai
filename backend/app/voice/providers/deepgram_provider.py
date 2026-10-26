import httpx

from app.core.config import settings

_URL = "https://api.deepgram.com/v1/listen"


_LANGUAGE_MODELS = {
    # nova-2 (the default) doesn't cover Marathi; nova-3 does.
    "mr": {"model": "nova-3", "language": "mr"},
}


class DeepgramTranscriber:
    def __init__(self) -> None:
        self._headers = {"Authorization": f"Token {settings.deepgram_api_key}"}

    async def transcribe(self, audio_bytes: bytes, content_type: str, language: str = "en") -> str:
        params = {"smart_format": "true", **_LANGUAGE_MODELS.get(language, {"model": "nova-2"})}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                _URL,
                headers={**self._headers, "Content-Type": content_type},
                params=params,
                content=audio_bytes,
            )
            response.raise_for_status()
            data = response.json()
            try:
                return data["results"]["channels"][0]["alternatives"][0]["transcript"]
            except (KeyError, IndexError):
                return ""
