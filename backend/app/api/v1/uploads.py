import hashlib
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Form, UploadFile, status

from app.api.deps import Auth, DbSession
from app.core.config import get_settings
from app.core.errors import AppError, NotFound
from app.domain.enums import Provenance, SourceKind
from app.repositories import ingestion_jobs as jobs_repo
from app.repositories import profiles as profile_repo
from app.repositories import sources as sources_repo
from app.schemas.ingestion import IngestionJobRead
from app.services.ingestion.keys import storage_key
from app.services.ingestion.validation import FileTooLarge, detect_and_validate
from app.services.storage import get_storage

router = APIRouter(prefix="/uploads", tags=["uploads"])

# `SourceKind.MANUAL` is for memories written directly in the app (see app/schemas/memory.py)
# and is never a valid upload kind.
UPLOADABLE_KINDS = {
    SourceKind.TEXT,
    SourceKind.PDF,
    SourceKind.DOCX,
    SourceKind.WHATSAPP,
    SourceKind.IMAGE,
    SourceKind.AUDIO,
    SourceKind.VIDEO,
}


class InvalidUploadKind(AppError):
    status_code = 422
    code = "validation_error"


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=IngestionJobRead)
async def upload_source(
    db: DbSession,
    auth: Auth,
    file: UploadFile,
    person_profile_id: Annotated[UUID, Form()],
    kind: Annotated[SourceKind, Form()],
    provenance: Annotated[Provenance, Form()] = Provenance.UNKNOWN,
) -> IngestionJobRead:
    if kind not in UPLOADABLE_KINDS:
        raise InvalidUploadKind(f"'{kind.value}' is not a kind that can be uploaded.")
    if profile_repo.get_owned(db, auth.user_id, person_profile_id) is None:
        raise NotFound("Profile not found")

    data = await file.read()
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise FileTooLarge(f"Files must be {get_settings().max_upload_mb} MB or smaller.")
    content_type = detect_and_validate(kind, data)

    source_id = uuid4()
    get_storage().save(storage_key(source_id), data, content_type)

    source = sources_repo.create(
        db,
        auth.user_id,
        person_profile_id,
        id=source_id,
        kind=kind,
        provenance=provenance,
        filename=file.filename,
        content_type=content_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        storage_key=storage_key(source_id),
    )
    job = jobs_repo.create(db, auth.user_id, person_profile_id, source.id)
    db.commit()
    return IngestionJobRead.model_validate(job)
