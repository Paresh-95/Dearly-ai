import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.personas import get_persona_or_404
from app.core.deps import get_current_user
from app.db.models import VoiceSample
from app.db.session import get_db
from app.storage.object_storage import delete_object, read_bytes, save_bytes
from app.voice.providers.fish_audio_provider import FishAudioVoiceProvider

router = APIRouter(
    prefix="/personas/{persona_id}/voice-samples", tags=["voice-samples"], dependencies=[Depends(get_current_user)]
)

_voice_provider = FishAudioVoiceProvider()

_ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a"}
_EXTENSION_MEDIA_TYPES = {"mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4"}
_MAX_SIZE_BYTES = 25 * 1024 * 1024  # 25MB
_MIN_SAMPLES_TO_CLONE = 1


def _content_type_plausible(content_type: str | None) -> bool:
    # Browsers report wildly inconsistent Content-Type for audio files
    # (especially .m4a/.wav across OSes) — sometimes empty, sometimes
    # application/octet-stream. The real validation is the extension
    # allowlist plus the magic-byte signature check below; this is only a
    # cheap first filter to reject obviously-wrong types (e.g. image/png).
    if not content_type:
        return True
    content_type = content_type.lower()
    return content_type.startswith("audio/") or content_type in {
        "application/octet-stream",
        "video/mp4",  # some browsers report m4a this way
    }


def _validate_audio_signature(data: bytes) -> bool:
    if data[:3] == b"ID3" or data[:2] == b"\xff\xfb":
        return True  # mp3
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return True  # wav
    if data[4:8] == b"ftyp":
        return True  # m4a/mp4 container
    return False


class VoiceSampleOut(BaseModel):
    id: uuid.UUID
    duration_seconds: float | None

    class Config:
        from_attributes = True


@router.post("", response_model=VoiceSampleOut)
async def upload_voice_sample(
    persona_id: uuid.UUID, file: UploadFile, db: AsyncSession = Depends(get_db)
) -> VoiceSample:
    persona = await get_persona_or_404(persona_id, db)

    extension = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if extension not in _ALLOWED_EXTENSIONS or not _content_type_plausible(file.content_type):
        raise HTTPException(status_code=400, detail="Unsupported audio file type")

    data = await file.read(_MAX_SIZE_BYTES + 1)
    if len(data) > _MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large")
    if not data or not _validate_audio_signature(data):
        raise HTTPException(status_code=400, detail="File does not look like a valid audio file")

    storage_path = save_bytes(f"voice_samples/{persona.id}", extension, data)

    sample = VoiceSample(persona_id=persona.id, storage_path=storage_path)
    db.add(sample)
    await db.commit()
    await db.refresh(sample)
    return sample


@router.get("", response_model=list[VoiceSampleOut])
async def list_voice_samples(persona_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[VoiceSample]:
    await get_persona_or_404(persona_id, db)
    result = await db.execute(select(VoiceSample).where(VoiceSample.persona_id == persona_id))
    return list(result.scalars().all())


@router.get("/{sample_id}/audio")
async def get_voice_sample_audio(
    persona_id: uuid.UUID, sample_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Response:
    await get_persona_or_404(persona_id, db)
    sample = await db.get(VoiceSample, sample_id)
    if sample is None or sample.persona_id != persona_id:
        raise HTTPException(status_code=404, detail="Voice sample not found")

    extension = sample.storage_path.rsplit(".", 1)[-1].lower()
    media_type = _EXTENSION_MEDIA_TYPES.get(extension, "application/octet-stream")
    data = read_bytes(sample.storage_path)
    return Response(content=data, media_type=media_type)


@router.delete("/{sample_id}", status_code=204)
async def delete_voice_sample(
    persona_id: uuid.UUID, sample_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    await get_persona_or_404(persona_id, db)
    sample = await db.get(VoiceSample, sample_id)
    if sample is None or sample.persona_id != persona_id:
        raise HTTPException(status_code=404, detail="Voice sample not found")

    delete_object(sample.storage_path)
    await db.delete(sample)
    await db.commit()


@router.post("/clone")
async def clone_voice(persona_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    persona = await get_persona_or_404(persona_id, db)
    result = await db.execute(select(VoiceSample).where(VoiceSample.persona_id == persona_id))
    samples = list(result.scalars().all())
    if len(samples) < _MIN_SAMPLES_TO_CLONE:
        raise HTTPException(status_code=400, detail="Upload at least one voice sample first")

    sample_bytes = [read_bytes(s.storage_path) for s in samples]
    voice_id = await _voice_provider.clone_voice(f"persona-{persona.id}", sample_bytes)

    persona.provider_voice_id = voice_id
    await db.commit()
    return {"provider_voice_id": voice_id}
