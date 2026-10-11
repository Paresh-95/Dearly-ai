from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import IndexStatus
from app.models import MemoryChunk
from app.services.retrieval.base import RetrievedChunk


def search(
    db: Session,
    *,
    user_id: UUID,
    person_profile_id: UUID,
    query_embedding: list[float],
    limit: int,
    memory_ids: list[UUID] | None = None,
) -> list[RetrievedChunk]:
    """Nearest neighbours by cosine distance, restricted to chunks that actually have an
    embedding (`index_status == 'indexed'`) — a `pending` chunk has no vector to compare."""
    distance = MemoryChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(MemoryChunk, distance.label("distance"))
        .where(
            MemoryChunk.user_id == user_id,
            MemoryChunk.person_profile_id == person_profile_id,
            MemoryChunk.index_status == IndexStatus.INDEXED,
        )
    )
    if memory_ids is not None:
        stmt = stmt.where(MemoryChunk.memory_id.in_(memory_ids))
    stmt = stmt.order_by(distance).limit(limit)

    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            memory_id=chunk.memory_id,
            text=chunk.text,
            metadata=chunk.meta,
            score=1.0 - float(distance),  # cosine similarity
        )
        for chunk, distance in db.execute(stmt).all()
    ]
