import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.personas import get_persona_or_404
from app.core.deps import get_current_user
from app.db.models import Memory, MemoryChunk
from app.db.session import get_db
from app.rag.chunking import chunk_memory
from app.rag.embeddings import embed_texts

router = APIRouter(
    prefix="/personas/{persona_id}/memories", tags=["memories"], dependencies=[Depends(get_current_user)]
)

_ALLOWED_TYPES = {
    "story",
    "fact",
    "trait",
    "quote",
    "value",
    "routine",
    "preference",
    "physical_detail",
    "advice",
    "regret",
    "timeline_event",
}
_TYPE_PATTERN = "^(" + "|".join(sorted(_ALLOWED_TYPES)) + ")$"
_MAX_TEXT_LEN = 8000


class MemoryCreate(BaseModel):
    type: str = Field(pattern=_TYPE_PATTERN)
    raw_text: str = Field(min_length=1, max_length=_MAX_TEXT_LEN)


class MemoryUpdate(BaseModel):
    type: str | None = Field(default=None, pattern=_TYPE_PATTERN)
    raw_text: str | None = Field(default=None, min_length=1, max_length=_MAX_TEXT_LEN)


class MemoryOut(BaseModel):
    id: uuid.UUID
    type: str
    raw_text: str

    class Config:
        from_attributes = True


@router.post("", response_model=MemoryOut)
async def create_memory(
    persona_id: uuid.UUID, payload: MemoryCreate, db: AsyncSession = Depends(get_db)
) -> Memory:
    persona = await get_persona_or_404(persona_id, db)

    memory = Memory(persona_id=persona.id, type=payload.type, raw_text=payload.raw_text.strip())
    db.add(memory)
    await db.flush()

    chunks = chunk_memory(memory.type, memory.raw_text)
    if chunks:
        embeddings = await embed_texts(chunks)
        for chunk_text, embedding in zip(chunks, embeddings):
            db.add(
                MemoryChunk(
                    memory_id=memory.id,
                    persona_id=persona.id,
                    chunk_text=chunk_text,
                    embedding=embedding,
                )
            )

    await db.commit()
    await db.refresh(memory)
    return memory


@router.get("", response_model=list[MemoryOut])
async def list_memories(persona_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[Memory]:
    await get_persona_or_404(persona_id, db)
    result = await db.execute(
        select(Memory).where(Memory.persona_id == persona_id).order_by(Memory.created_at.desc())
    )
    return list(result.scalars().all())


@router.patch("/{memory_id}", response_model=MemoryOut)
async def update_memory(
    persona_id: uuid.UUID, memory_id: uuid.UUID, payload: MemoryUpdate, db: AsyncSession = Depends(get_db)
) -> Memory:
    persona = await get_persona_or_404(persona_id, db)
    memory = await db.get(Memory, memory_id)
    if memory is None or memory.persona_id != persona_id:
        raise HTTPException(status_code=404, detail="Memory not found")

    if payload.type is not None:
        memory.type = payload.type
    if payload.raw_text is not None:
        memory.raw_text = payload.raw_text.strip()

    # Re-chunk/re-embed from scratch whenever either field changes, since
    # chunking depends on both the text and the type (atomic vs. split).
    if payload.type is not None or payload.raw_text is not None:
        old_chunks = (
            await db.execute(select(MemoryChunk).where(MemoryChunk.memory_id == memory.id))
        ).scalars().all()
        for chunk in old_chunks:
            await db.delete(chunk)
        await db.flush()

        chunks = chunk_memory(memory.type, memory.raw_text)
        if chunks:
            embeddings = await embed_texts(chunks)
            for chunk_text, embedding in zip(chunks, embeddings):
                db.add(
                    MemoryChunk(
                        memory_id=memory.id,
                        persona_id=persona.id,
                        chunk_text=chunk_text,
                        embedding=embedding,
                    )
                )

    await db.commit()
    await db.refresh(memory)
    return memory


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(persona_id: uuid.UUID, memory_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await get_persona_or_404(persona_id, db)
    memory = await db.get(Memory, memory_id)
    if memory is None or memory.persona_id != persona_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    await db.delete(memory)
    await db.commit()
