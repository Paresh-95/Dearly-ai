"""Orchestrates one retrieval request: resolve metadata filters -> dense and/or keyword
search -> fuse (hybrid only) -> rerank -> truncate to `limit`. Stops at evidence selection —
turning that evidence into a generated answer is Milestone 6, not here."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MemoryStatus
from app.models import Memory, MemoryPerson
from app.services.providers.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.providers.errors import ProviderNotConfigured
from app.services.retrieval import dense, keyword
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.reranker import LexicalOverlapReranker, Reranker

SearchMode = Literal["dense", "keyword", "hybrid"]


@dataclass
class EvidenceItem:
    memory_id: UUID
    chunk_id: UUID
    text: str
    metadata: dict[str, Any]
    score: float


def _resolve_memory_filter(
    db: Session,
    *,
    person_profile_id: UUID,
    category: str | None,
    date_from: date | None,
    date_to: date | None,
    people: list[str] | None,
) -> list[UUID] | None:
    """None means "no extra filter"; a list (possibly empty) means "only these memory ids"."""
    if not any([category, date_from, date_to, people]):
        return None

    filters = [
        Memory.person_profile_id == person_profile_id,
        Memory.status == MemoryStatus.APPROVED,
    ]
    if category:
        filters.append(Memory.category == category)
    if date_from:
        filters.append(Memory.date_start.is_not(None) & (Memory.date_start >= date_from))
    if date_to:
        filters.append(Memory.date_start.is_not(None) & (Memory.date_start <= date_to))
    ids = set(db.scalars(select(Memory.id).where(*filters)))

    if people:
        people_ids = set(
            db.scalars(
                select(MemoryPerson.memory_id).where(
                    MemoryPerson.person_profile_id == person_profile_id,
                    MemoryPerson.name.in_(people),
                )
            )
        )
        ids &= people_ids

    return list(ids)


def search(
    db: Session,
    *,
    user_id: UUID,
    person_profile_id: UUID,
    query: str,
    mode: SearchMode = "hybrid",
    limit: int = 8,
    candidate_limit: int = 30,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    people: list[str] | None = None,
    rrf_k: int = 60,
    get_provider: Callable[[], EmbeddingProvider] | None = None,
    reranker: Reranker | None = None,
) -> tuple[list[EvidenceItem], dict[str, Any]]:
    reranker = reranker or LexicalOverlapReranker()
    diagnostics: dict[str, Any] = {"dense_count": 0, "keyword_count": 0, "fused_count": 0}

    memory_ids = _resolve_memory_filter(
        db,
        person_profile_id=person_profile_id,
        category=category,
        date_from=date_from,
        date_to=date_to,
        people=people,
    )
    if memory_ids is not None and not memory_ids:
        return [], diagnostics  # filters matched no memories at all; nothing to search

    dense_results: list = []
    keyword_results: list = []

    if mode in ("dense", "hybrid"):
        try:
            provider = (get_provider or get_embedding_provider)()
            [query_vector] = provider.embed([query])
            dense_results = dense.search(
                db,
                user_id=user_id,
                person_profile_id=person_profile_id,
                query_embedding=query_vector,
                limit=candidate_limit,
                memory_ids=memory_ids,
            )
        except ProviderNotConfigured as exc:
            diagnostics["dense_error"] = str(exc)

    if mode in ("keyword", "hybrid"):
        keyword_results = keyword.search(
            db,
            user_id=user_id,
            person_profile_id=person_profile_id,
            query=query,
            limit=candidate_limit,
            memory_ids=memory_ids,
        )

    diagnostics["dense_count"] = len(dense_results)
    diagnostics["keyword_count"] = len(keyword_results)

    if mode == "dense":
        fused = [(c, c.score) for c in dense_results]
    elif mode == "keyword":
        fused = [(c, c.score) for c in keyword_results]
    else:
        fused = reciprocal_rank_fusion([dense_results, keyword_results], k=rrf_k)
    diagnostics["fused_count"] = len(fused)

    candidates = [c for c, _ in fused]
    reranked = reranker.rerank(query, candidates)

    items = [
        EvidenceItem(
            memory_id=c.memory_id,
            chunk_id=c.chunk_id,
            text=c.text,
            metadata=c.metadata,
            score=score,
        )
        for c, score in reranked[:limit]
    ]
    return items, diagnostics
