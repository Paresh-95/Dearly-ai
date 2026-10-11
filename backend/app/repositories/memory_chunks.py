"""Chunking + embedding for approved memories. The only entry points are `reindex_memory`
(called from `app.repositories.memories.approve`, and from the standalone `/reindex` endpoint
to retry chunks left `pending` after a provider wasn't configured) and `clear_chunks` (called
whenever a memory leaves `approved` — see `memories.update` and `memories.reject`)."""

import hashlib
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.enums import IndexStatus
from app.models import Memory, MemoryChunk, MemoryPerson
from app.services.chunking.chunker import chunk_memory
from app.services.providers.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.providers.errors import ProviderNotConfigured


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def list_for_memory(db: Session, memory_id: UUID) -> list[MemoryChunk]:
    stmt = (
        select(MemoryChunk)
        .where(MemoryChunk.memory_id == memory_id)
        .order_by(MemoryChunk.chunk_index)
    )
    return list(db.scalars(stmt))


def clear_chunks(db: Session, memory_id: UUID) -> None:
    db.query(MemoryChunk).filter(MemoryChunk.memory_id == memory_id).delete()
    db.flush()


def reindex_memory(
    db: Session,
    memory: Memory,
    *,
    get_provider: Callable[[], EmbeddingProvider] | None = None,
) -> list[MemoryChunk]:
    """Chunks the memory's current content and re-embeds only the chunks whose content
    actually changed since they were last indexed (see docs/decisions/0004). If no embedding
    provider is configured, chunks are written with `index_status='pending'` and no
    embedding — the memory stays approved; it just isn't searchable until a provider is
    configured and this is retried (see `POST /memories/{id}/reindex`).

    `get_provider` defaults to None (not directly to `get_embedding_provider`) so that
    tests can `monkeypatch.setattr` this module's `get_embedding_provider` and have it take
    effect through `approve()`/`reject()`, which call this without passing one — a default
    bound directly to the function would capture it once at import time and never see the
    patched version."""
    get_provider = get_provider or get_embedding_provider
    settings = get_settings()
    people_names = [
        p.name for p in db.scalars(select(MemoryPerson).where(MemoryPerson.memory_id == memory.id))
    ]
    quotations = [q.get("text", "") for q in memory.quotations]

    drafts = chunk_memory(
        title=memory.title,
        description=memory.description,
        quotations=quotations,
        category=memory.category,
        date_text=memory.date_text,
        location=memory.location,
        people=people_names,
        max_chars=settings.chunk_max_chars,
    )

    existing = {c.chunk_index: c for c in list_for_memory(db, memory.id)}
    rows: dict[int, MemoryChunk] = {}
    to_embed: list[tuple[int, str]] = []

    for i, draft in enumerate(drafts):
        content_hash = _content_hash(draft.text)
        row = existing.get(i)
        if row is None:
            row = MemoryChunk(
                user_id=memory.user_id,
                person_profile_id=memory.person_profile_id,
                memory_id=memory.id,
                chunk_index=i,
            )
            db.add(row)
        row.text = draft.text
        row.meta = draft.metadata
        rows[i] = row

        if row.content_hash == content_hash and row.index_status == IndexStatus.INDEXED:
            continue  # unchanged and already embedded: no provider call needed
        row.content_hash = content_hash
        row.index_status = IndexStatus.PENDING
        row.embedding = None
        to_embed.append((i, draft.text))

    for index, row in existing.items():
        if index >= len(drafts):  # the memory got shorter; drop the extra chunk
            db.delete(row)

    db.flush()

    if to_embed:
        try:
            provider = get_provider()
            vectors = provider.embed([text for _, text in to_embed])
        except ProviderNotConfigured:
            pass  # left `pending`; retried later via get_provider() once configured
        else:
            for (index, _), vector in zip(to_embed, vectors, strict=True):
                row = rows[index]
                row.embedding = vector
                row.embedding_model = provider.model_name
                row.index_status = IndexStatus.INDEXED
            db.flush()

    return [rows[i] for i in sorted(rows)]
