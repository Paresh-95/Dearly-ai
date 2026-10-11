from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MemoryChunk
from app.services.retrieval.base import RetrievedChunk
from app.services.retrieval.tokenize import tokenize_words


def _or_query(query: str) -> str | None:
    """`websearch_to_tsquery` ANDs every word together (confirmed by actually running the
    Milestone 5 evaluation harness: a natural question like "What did Mum make for
    breakfast on Sundays?" requires 'what', 'did', 'for' and 'on' to ALL appear in the
    chunk too, so it matched nothing). People ask full questions, not keyword strings, so
    this ORs the extracted words instead -- `ts_rank` still rewards a chunk that matches
    more of them over one that matches only one. Returns None for a query with no words at
    all (e.g. pure punctuation)."""
    words = tokenize_words(query.lower())
    return " | ".join(words) if words else None


def search(
    db: Session,
    *,
    user_id: UUID,
    person_profile_id: UUID,
    query: str,
    limit: int,
    memory_ids: list[UUID] | None = None,
) -> list[RetrievedChunk]:
    """Postgres full-text search. Unlike dense search, this does not require an embedding —
    a chunk left `pending` because no embedding provider is configured is still fully
    keyword-searchable, since `tsv` is generated straight from `text` (see migration 0001)."""
    or_query = _or_query(query)
    if or_query is None:
        return []

    tsquery = func.to_tsquery("simple", or_query)
    rank = func.ts_rank(MemoryChunk.tsv, tsquery)
    stmt = select(MemoryChunk, rank.label("rank")).where(
        MemoryChunk.user_id == user_id,
        MemoryChunk.person_profile_id == person_profile_id,
        MemoryChunk.tsv.op("@@")(tsquery),
    )
    if memory_ids is not None:
        stmt = stmt.where(MemoryChunk.memory_id.in_(memory_ids))
    stmt = stmt.order_by(rank.desc()).limit(limit)

    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            memory_id=chunk.memory_id,
            text=chunk.text,
            metadata=chunk.meta,
            score=float(rank_value),
        )
        for chunk, rank_value in db.execute(stmt).all()
    ]
