from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import Auth, DbSession
from app.core.errors import NotFound
from app.repositories import sources as sources_repo
from app.schemas.ingestion import SourceList, SourceRead, SourceSegmentList, SourceSegmentRead
from app.services.storage import get_storage

router = APIRouter(prefix="/sources", tags=["sources"])


def _get_owned_or_404(db: DbSession, auth: Auth, source_id: UUID):  # noqa: ANN001, ANN202
    source = sources_repo.get_owned(db, auth.user_id, source_id)
    if source is None:
        raise NotFound("Source not found")
    return source


@router.get("", response_model=SourceList)
def list_sources(db: DbSession, auth: Auth, person_profile_id: UUID | None = None) -> SourceList:
    items = sources_repo.list_for_user(db, auth.user_id, person_profile_id=person_profile_id)
    return SourceList(items=[SourceRead.model_validate(s) for s in items])


@router.get("/{source_id}", response_model=SourceRead)
def get_source(source_id: UUID, db: DbSession, auth: Auth) -> SourceRead:
    return SourceRead.model_validate(_get_owned_or_404(db, auth, source_id))


@router.get("/{source_id}/segments", response_model=SourceSegmentList)
def get_source_segments(source_id: UUID, db: DbSession, auth: Auth) -> SourceSegmentList:
    _get_owned_or_404(db, auth, source_id)
    segments = sources_repo.segments_for(db, source_id)
    return SourceSegmentList(items=[SourceSegmentRead.model_validate(s) for s in segments])


@router.get("/{source_id}/download")
def download_source(source_id: UUID, db: DbSession, auth: Auth) -> Response:
    """The only way to read an original file back: an authenticated, ownership-checked API
    call — there is no public or signed URL that bypasses this."""
    source = _get_owned_or_404(db, auth, source_id)
    data = get_storage().read(source.storage_key)
    filename = source.filename or f"{source.id}"
    return Response(
        content=data,
        media_type=source.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: UUID, db: DbSession, auth: Auth) -> None:
    source = _get_owned_or_404(db, auth, source_id)
    get_storage().delete(source.storage_key)
    sources_repo.delete(db, source)
    db.commit()
