import time

from fastapi import APIRouter

from app.api.deps import Auth, DbSession
from app.core.errors import NotFound
from app.repositories import profiles as profile_repo
from app.schemas.retrieval import (
    RetrievalDiagnostics,
    RetrievalResultItem,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from app.services.retrieval import pipeline

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalSearchResponse)
def search_memories(
    body: RetrievalSearchRequest, db: DbSession, auth: Auth
) -> RetrievalSearchResponse:
    if profile_repo.get_owned(db, auth.user_id, body.person_profile_id) is None:
        raise NotFound("Profile not found")

    started = time.perf_counter()
    items, diagnostics = pipeline.search(
        db,
        user_id=auth.user_id,
        person_profile_id=body.person_profile_id,
        query=body.query,
        mode=body.mode,
        limit=body.limit,
        category=body.category,
        date_from=body.date_from,
        date_to=body.date_to,
        people=body.people,
    )
    took_ms = (time.perf_counter() - started) * 1000

    return RetrievalSearchResponse(
        items=[
            RetrievalResultItem(
                memory_id=i.memory_id,
                chunk_id=i.chunk_id,
                text=i.text,
                score=i.score,
                metadata=i.metadata,
            )
            for i in items
        ],
        diagnostics=RetrievalDiagnostics(mode_used=body.mode, took_ms=took_ms, **diagnostics),
    )
