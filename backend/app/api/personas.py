import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models import Persona
from app.db.session import get_db
from app.storage.object_storage import delete_object, read_bytes, save_bytes

router = APIRouter(prefix="/personas", tags=["personas"], dependencies=[Depends(get_current_user)])

_ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
_MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5MB
_PHOTO_CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def _content_type_plausible(content_type: str | None) -> bool:
    if not content_type:
        return True
    content_type = content_type.lower()
    return content_type.startswith("image/") or content_type == "application/octet-stream"


def _validate_image_signature(data: bytes) -> bool:
    if data[:3] == b"\xff\xd8\xff":
        return True  # jpeg
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True  # png
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True  # webp
    return False


_SUPPORTED_LANGUAGES = {"en", "mr"}
_SUPPORTED_VOICE_PROVIDERS = {"fish_audio", "sarvam"}
_SUPPORTED_GENDERS = {"male", "female", "other"}


def _validate_gender(value: str | None) -> str | None:
    if value is not None and value not in _SUPPORTED_GENDERS:
        raise ValueError(f"Unsupported gender. Choose one of: {', '.join(sorted(_SUPPORTED_GENDERS))}")
    return value


class PersonaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    relationship_to_user: str = Field(default="", max_length=200)
    gender: str | None = None
    user_relationship: str = Field(default="", max_length=200)
    user_gender: str | None = None
    personality_notes: dict = Field(default_factory=dict)
    language: str = Field(default="en")

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        if value not in _SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language. Choose one of: {', '.join(sorted(_SUPPORTED_LANGUAGES))}")
        return value

    @field_validator("gender", "user_gender")
    @classmethod
    def _validate_genders(cls, value: str | None) -> str | None:
        return _validate_gender(value)


class PersonaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    relationship_to_user: str | None = Field(default=None, max_length=200)
    gender: str | None = None
    user_relationship: str | None = Field(default=None, max_length=200)
    user_gender: str | None = None
    personality_notes: dict | None = None
    language: str | None = None
    voice_provider: str | None = None

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str | None) -> str | None:
        if value is not None and value not in _SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language. Choose one of: {', '.join(sorted(_SUPPORTED_LANGUAGES))}")
        return value

    @field_validator("voice_provider")
    @classmethod
    def _validate_voice_provider(cls, value: str | None) -> str | None:
        if value is not None and value not in _SUPPORTED_VOICE_PROVIDERS:
            raise ValueError(f"Unsupported voice provider. Choose one of: {', '.join(sorted(_SUPPORTED_VOICE_PROVIDERS))}")
        return value

    @field_validator("gender", "user_gender")
    @classmethod
    def _validate_genders(cls, value: str | None) -> str | None:
        return _validate_gender(value)


class PersonaOut(BaseModel):
    id: uuid.UUID
    name: str
    relationship_to_user: str
    gender: str | None
    user_relationship: str
    user_gender: str | None
    personality_notes: dict
    language: str
    provider_voice_id: str | None
    sarvam_voice_id: str | None
    voice_provider: str
    has_photo: bool
    has_voice: bool

    class Config:
        from_attributes = True

    @staticmethod
    def from_persona(persona: Persona) -> "PersonaOut":
        active_voice_id = (
            persona.sarvam_voice_id if persona.voice_provider == "sarvam" else persona.provider_voice_id
        )
        return PersonaOut(
            id=persona.id,
            name=persona.name,
            relationship_to_user=persona.relationship_to_user,
            gender=persona.gender,
            user_relationship=persona.user_relationship,
            user_gender=persona.user_gender,
            personality_notes=persona.personality_notes,
            language=persona.language,
            provider_voice_id=persona.provider_voice_id,
            sarvam_voice_id=persona.sarvam_voice_id,
            voice_provider=persona.voice_provider,
            has_photo=persona.photo_path is not None,
            has_voice=active_voice_id is not None,
        )


@router.post("", response_model=PersonaOut)
async def create_persona(payload: PersonaCreate, db: AsyncSession = Depends(get_db)) -> PersonaOut:
    persona = Persona(
        name=payload.name,
        relationship_to_user=payload.relationship_to_user,
        gender=payload.gender,
        user_relationship=payload.user_relationship,
        user_gender=payload.user_gender,
        personality_notes=payload.personality_notes,
        language=payload.language,
    )
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return PersonaOut.from_persona(persona)


@router.get("", response_model=list[PersonaOut])
async def list_personas(db: AsyncSession = Depends(get_db)) -> list[PersonaOut]:
    result = await db.execute(select(Persona).order_by(Persona.created_at.desc()))
    return [PersonaOut.from_persona(p) for p in result.scalars().all()]


async def get_persona_or_404(persona_id: uuid.UUID, db: AsyncSession) -> Persona:
    persona = await db.get(Persona, persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.get("/{persona_id}", response_model=PersonaOut)
async def get_persona(persona_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> PersonaOut:
    persona = await get_persona_or_404(persona_id, db)
    return PersonaOut.from_persona(persona)


@router.patch("/{persona_id}", response_model=PersonaOut)
async def update_persona(
    persona_id: uuid.UUID, payload: PersonaUpdate, db: AsyncSession = Depends(get_db)
) -> PersonaOut:
    persona = await get_persona_or_404(persona_id, db)

    if payload.voice_provider == "sarvam" and not persona.sarvam_voice_id:
        raise HTTPException(status_code=400, detail="No Sarvam voice configured for this persona yet")
    if payload.voice_provider == "fish_audio" and not persona.provider_voice_id:
        raise HTTPException(status_code=400, detail="No Fish Audio voice configured for this persona yet")

    if payload.name is not None:
        persona.name = payload.name
    if payload.relationship_to_user is not None:
        persona.relationship_to_user = payload.relationship_to_user
    if payload.gender is not None:
        persona.gender = payload.gender
    if payload.user_relationship is not None:
        persona.user_relationship = payload.user_relationship
    if payload.user_gender is not None:
        persona.user_gender = payload.user_gender
    if payload.personality_notes is not None:
        persona.personality_notes = payload.personality_notes
    if payload.language is not None:
        persona.language = payload.language
    if payload.voice_provider is not None:
        persona.voice_provider = payload.voice_provider

    await db.commit()
    await db.refresh(persona)
    return PersonaOut.from_persona(persona)


@router.post("/{persona_id}/photo", response_model=PersonaOut)
async def upload_persona_photo(
    persona_id: uuid.UUID, file: UploadFile, db: AsyncSession = Depends(get_db)
) -> PersonaOut:
    persona = await get_persona_or_404(persona_id, db)

    extension = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if extension not in _ALLOWED_PHOTO_EXTENSIONS or not _content_type_plausible(file.content_type):
        raise HTTPException(status_code=400, detail="Unsupported image file type")

    data = await file.read(_MAX_PHOTO_BYTES + 1)
    if len(data) > _MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="Image too large")
    if not data or not _validate_image_signature(data):
        raise HTTPException(status_code=400, detail="File does not look like a valid image")

    old_photo_path = persona.photo_path
    persona.photo_path = save_bytes(f"persona_photos/{persona.id}", extension, data)
    await db.commit()
    await db.refresh(persona)

    if old_photo_path:
        delete_object(old_photo_path)

    return PersonaOut.from_persona(persona)


@router.get("/{persona_id}/photo")
async def get_persona_photo(persona_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Response:
    persona = await get_persona_or_404(persona_id, db)
    if not persona.photo_path:
        raise HTTPException(status_code=404, detail="No photo uploaded")

    extension = persona.photo_path.rsplit(".", 1)[-1].lower()
    content_type = _PHOTO_CONTENT_TYPES.get(extension, "application/octet-stream")
    data = read_bytes(persona.photo_path)
    return Response(content=data, media_type=content_type)


@router.delete("/{persona_id}", status_code=204)
async def delete_persona(persona_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    persona = await get_persona_or_404(persona_id, db)
    photo_path = persona.photo_path
    await db.delete(persona)
    await db.commit()
    if photo_path:
        delete_object(photo_path)
