from uuid import UUID

from fastapi import APIRouter

from app.api.deps import Auth, DbSession
from app.core.errors import NotFound
from app.repositories import ingestion_jobs as jobs_repo
from app.schemas.ingestion import IngestionJobList, IngestionJobRead

router = APIRouter(prefix="/ingestion-jobs", tags=["ingestion-jobs"])


@router.get("", response_model=IngestionJobList)
def list_jobs(
    db: DbSession, auth: Auth, person_profile_id: UUID | None = None
) -> IngestionJobList:
    items = jobs_repo.list_for_user(db, auth.user_id, person_profile_id=person_profile_id)
    return IngestionJobList(items=[IngestionJobRead.model_validate(j) for j in items])


@router.get("/{job_id}", response_model=IngestionJobRead)
def get_job(job_id: UUID, db: DbSession, auth: Auth) -> IngestionJobRead:
    job = jobs_repo.get_owned(db, auth.user_id, job_id)
    if job is None:
        raise NotFound("Ingestion job not found")
    return IngestionJobRead.model_validate(job)
