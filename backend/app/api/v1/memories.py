from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import Auth, DbSession, OwnedMemory
from app.core.errors import Conflict, NotFound
from app.domain.enums import MemoryStatus
from app.repositories import memories as repo
from app.repositories import memory_chunks as chunks_repo
from app.repositories import profiles as profile_repo
from app.schemas.memory import (
    MemoryChunkList,
    MemoryChunkRead,
    MemoryCreate,
    MemoryList,
    MemoryRead,
    MemoryRejectRequest,
    MemoryUpdate,
)

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=MemoryRead)
def create_memory(body: MemoryCreate, db: DbSession, auth: Auth) -> MemoryRead:
    # The profile must belong to the caller; referencing someone else's profile looks like
    # referencing a missing one (no existence leak), same as GET /profiles/{id}.
    if profile_repo.get_owned(db, auth.user_id, body.person_profile_id) is None:
        raise NotFound("Profile not found")
    memory = repo.create(db, auth.user_id, body)
    db.commit()
    return MemoryRead.model_validate(memory)


@router.get("", response_model=MemoryList)
def list_memories(
    db: DbSession,
    auth: Auth,
    person_profile_id: UUID | None = None,
    status_: MemoryStatus | None = Query(default=None, alias="status"),  # noqa: B008
    category: str | None = None,
    q: str | None = Query(default=None, max_length=200),  # noqa: B008
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
) -> MemoryList:
    items, next_cursor, total = repo.list_for_user(
        db,
        auth.user_id,
        person_profile_id=person_profile_id,
        status=status_,
        category=category,
        q=q,
        limit=limit,
        cursor=cursor,
    )
    return MemoryList(
        items=[MemoryRead.model_validate(m) for m in items], next_cursor=next_cursor, total=total
    )


@router.get("/{memory_id}", response_model=MemoryRead)
def get_memory(memory: OwnedMemory) -> MemoryRead:
    return MemoryRead.model_validate(memory)


@router.patch("/{memory_id}", response_model=MemoryRead)
def update_memory(memory: OwnedMemory, body: MemoryUpdate, db: DbSession) -> MemoryRead:
    memory = repo.update(db, memory, body)
    db.commit()
    return MemoryRead.model_validate(memory)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory: OwnedMemory, db: DbSession) -> None:
    repo.delete(db, memory)
    db.commit()


@router.post("/{memory_id}/approve", response_model=MemoryRead)
def approve_memory(memory: OwnedMemory, db: DbSession) -> MemoryRead:
    memory = repo.approve(db, memory)
    db.commit()
    return MemoryRead.model_validate(memory)


@router.post("/{memory_id}/reject", response_model=MemoryRead)
def reject_memory(memory: OwnedMemory, body: MemoryRejectRequest, db: DbSession) -> MemoryRead:
    memory = repo.reject(db, memory, body.note)
    db.commit()
    return MemoryRead.model_validate(memory)


@router.get("/{memory_id}/chunks", response_model=MemoryChunkList)
def get_memory_chunks(memory: OwnedMemory, db: DbSession) -> MemoryChunkList:
    chunks = chunks_repo.list_for_memory(db, memory.id)
    return MemoryChunkList(items=[MemoryChunkRead.model_validate(c) for c in chunks])


@router.post("/{memory_id}/reindex", response_model=MemoryChunkList)
def reindex_memory(memory: OwnedMemory, db: DbSession) -> MemoryChunkList:
    """Retries chunking/embedding for an approved memory — mainly useful to pick up chunks
    left `pending` because no embedding provider was configured the first time around."""
    if memory.status != MemoryStatus.APPROVED:
        raise Conflict("Only an approved memory can be (re)indexed.")
    chunks = chunks_repo.reindex_memory(db, memory)
    db.commit()
    return MemoryChunkList(items=[MemoryChunkRead.model_validate(c) for c in chunks])
