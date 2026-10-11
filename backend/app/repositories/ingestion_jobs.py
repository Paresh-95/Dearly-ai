from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import JobState
from app.models import IngestionJob


def create(db: Session, user_id: UUID, person_profile_id: UUID, source_id: UUID) -> IngestionJob:
    job = IngestionJob(user_id=user_id, person_profile_id=person_profile_id, source_id=source_id)
    db.add(job)
    db.flush()
    return job


def get_owned(db: Session, user_id: UUID, job_id: UUID) -> IngestionJob | None:
    return db.scalar(
        select(IngestionJob).where(IngestionJob.id == job_id, IngestionJob.user_id == user_id)
    )


def list_for_user(
    db: Session, user_id: UUID, *, person_profile_id: UUID | None = None, limit: int = 50
) -> list[IngestionJob]:
    stmt = select(IngestionJob).where(IngestionJob.user_id == user_id)
    if person_profile_id is not None:
        stmt = stmt.where(IngestionJob.person_profile_id == person_profile_id)
    return list(db.scalars(stmt.order_by(IngestionJob.created_at.desc()).limit(limit)))


def claim_next(db: Session, worker_id: str) -> IngestionJob | None:
    """Atomically claim one due job for this worker. `FOR UPDATE SKIP LOCKED` lets several
    worker processes poll the same table without blocking each other or double-claiming."""
    stmt = (
        select(IngestionJob)
        .where(IngestionJob.state == JobState.QUEUED, IngestionJob.run_after <= datetime.now(UTC))
        .order_by(IngestionJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = db.scalar(stmt)
    if job is None:
        return None
    job.state = JobState.RUNNING
    job.locked_at = datetime.now(UTC)
    job.locked_by = worker_id
    job.attempts += 1
    db.flush()
    return job


def mark_progress(
    db: Session, job: IngestionJob, *, stage: str, progress: int | None = None
) -> None:
    job.stage = stage
    job.progress = progress
    db.flush()


def mark_succeeded(db: Session, job: IngestionJob) -> None:
    job.state = JobState.SUCCEEDED
    job.error = None
    job.progress = 100
    job.finished_at = datetime.now(UTC)
    db.flush()


def mark_failed(db: Session, job: IngestionJob, error: str, *, max_attempts: int) -> None:
    """Retries with a short backoff until `max_attempts`, then fails for good — the job's
    `state`/`error`/`attempts` are what the review-facing UI reads, so a failure is always
    visible rather than silently retried forever."""
    job.error = error[:4000]
    if job.attempts >= max_attempts:
        job.state = JobState.FAILED
        job.finished_at = datetime.now(UTC)
    else:
        job.state = JobState.QUEUED
        job.run_after = datetime.now(UTC) + timedelta(seconds=30 * job.attempts)
    db.flush()
