import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MemoryChunk, Person
from app.rag.embeddings import embed_text

logger = logging.getLogger(__name__)


async def retrieve_relevant_chunks(
    db: AsyncSession, persona_id: uuid.UUID, query: str, top_k: int = 6
) -> list[MemoryChunk]:
    """Vector-similarity search scoped to a single persona.

    persona_id is a hard filter (not just similarity ranking) so retrieval can
    never leak another persona's memories.
    """
    try:
        query_embedding = await embed_text(query)
    except Exception:
        # Retrieval is an enhancement on top of the conversation, not a
        # precondition for it (ordinary small talk doesn't need any
        # retrieved memory anyway) — if the embeddings provider is down or
        # rate-limited, still let the turn proceed without memories instead
        # of failing the whole conversation.
        logger.exception("Memory retrieval embedding failed for persona %s; proceeding with no memories", persona_id)
        return []

    stmt = (
        select(MemoryChunk)
        .where(MemoryChunk.persona_id == persona_id)
        .order_by(MemoryChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def find_mentioned_people(db: AsyncSession, persona_id: uuid.UUID, query: str) -> list[Person]:
    """Which of this persona's known people are named in the user's turn.

    Relation facts are a small, structured set per persona (handfuls of
    rows, not hundreds) — a direct case-insensitive name match against the
    turn text is simpler and more reliable here than embedding similarity,
    which can miss an exact name or surface an unrelated person instead.
    """
    result = await db.execute(select(Person).where(Person.persona_id == persona_id))
    people = list(result.scalars().all())
    if not people:
        return []

    query_lower = query.lower()
    return [p for p in people if p.name and p.name.lower() in query_lower]
