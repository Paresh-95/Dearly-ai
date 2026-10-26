from typing import Protocol


class TranscriberProtocol(Protocol):
    async def transcribe(self, audio_bytes: bytes, content_type: str) -> str: ...


class VoiceCloneProtocol(Protocol):
    async def clone_voice(self, name: str, sample_bytes_list: list[bytes]) -> str:
        """Returns a provider-specific voice id."""
        ...

    async def synthesize(self, text: str, voice_id: str, language: str = "en", mood: str | None = None) -> bytes:
        """Returns audio bytes (mp3). `mood` is an optional emotional
        delivery cue (see app.llm.prompt_builder.MOOD_OPTIONS)."""
        ...
