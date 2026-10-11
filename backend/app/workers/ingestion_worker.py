"""The ingestion worker: claims one due job at a time from the Postgres-backed queue,
extracts text, and (when an LLM provider is configured) proposes memory candidates for
review. Runs as its own process (see infra/docker/backend.Dockerfile's `worker` stage and
docker-compose.yml's `worker` service); `process_one` is also called directly by tests."""

import logging
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.domain.enums import SourceKind
from app.models import PersonProfile
from app.repositories import ingestion_jobs as jobs_repo
from app.repositories import memories as memories_repo
from app.repositories import sources as sources_repo
from app.services.extraction.base import ExtractionError
from app.services.extraction.pipeline import NEEDS_TRANSCRIBER, extract
from app.services.providers.errors import ProviderNotConfigured
from app.services.providers.llm import MemoryCandidateExtractor, get_candidate_extractor
from app.services.providers.stt import SpeechTranscriber, get_speech_transcriber
from app.services.storage import ObjectStorage, get_storage

log = logging.getLogger("app.workers.ingestion")

# Failures with a clear, user-facing cause; anything else is logged in full but shown to the
# user as a generic message so internal details never leak into job.error.
_EXPECTED_FAILURES = (ExtractionError, ProviderNotConfigured)


@contextmanager
def _materialize_if_needed(kind: SourceKind, data: bytes) -> Iterator[Path | None]:
    """Audio/video extraction needs a real file on disk (ffmpeg, and the STT SDK's upload);
    everything else works directly from bytes."""
    if kind not in NEEDS_TRANSCRIBER:
        yield None
        return
    suffix = ".mp4" if kind == SourceKind.VIDEO else ".audio"
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(data)
        tmp.flush()
        yield Path(tmp.name)


def _profile_context(db: Session, person_profile_id) -> str:  # noqa: ANN001
    profile = db.get(PersonProfile, person_profile_id)
    return f"{profile.name} ({profile.relationship})" if profile else ""


def process_one(
    db: Session,
    worker_id: str,
    *,
    storage: ObjectStorage | None = None,
    get_transcriber: Callable[[], SpeechTranscriber] = get_speech_transcriber,
    get_extractor: Callable[[], MemoryCandidateExtractor] = get_candidate_extractor,
) -> bool:
    """Claims and fully processes one due job. Returns False when there was nothing to do."""
    job = jobs_repo.claim_next(db, worker_id)
    if job is None:
        return False
    user_id, job_id = job.user_id, job.id  # stable values, independent of later rollbacks
    db.commit()  # release the row lock promptly

    storage = storage or get_storage()
    source = sources_repo.get_owned(db, user_id, job.source_id)

    try:
        jobs_repo.mark_progress(db, job, stage="extracting")
        db.commit()

        data = storage.read(source.storage_key)
        kind = SourceKind(source.kind)
        transcriber = get_transcriber() if kind in NEEDS_TRANSCRIBER else None

        with _materialize_if_needed(kind, data) as file_path:
            segments, metadata = extract(kind, data, file_path=file_path, transcriber=transcriber)

        if metadata:
            sources_repo.merge_metadata(db, source, metadata)
        segment_rows = sources_repo.replace_segments(db, source, segments)
        db.commit()

        jobs_repo.mark_progress(db, job, stage="identifying_memories", progress=60)
        db.commit()

        if segments:
            extractor = get_extractor()  # raises ProviderNotConfigured if unset
            candidates = extractor.extract(
                segments=segments, profile_context=_profile_context(db, job.person_profile_id)
            )
            segments_by_ordinal = {i + 1: row for i, row in enumerate(segment_rows)}
            for candidate in candidates:
                memories_repo.create_from_candidate(
                    db,
                    user_id,
                    job.person_profile_id,
                    source.id,
                    candidate,
                    segments_by_ordinal,
                )
            db.commit()

        jobs_repo.mark_succeeded(db, job)
        db.commit()
    except Exception as exc:
        db.rollback()
        job = jobs_repo.get_owned(db, user_id, job_id)
        if isinstance(exc, _EXPECTED_FAILURES):
            message = str(exc)
        else:
            log.exception("ingestion job %s failed unexpectedly", job_id)
            message = "An unexpected error occurred while processing this file."
        jobs_repo.mark_failed(db, job, message, max_attempts=get_settings().worker_max_attempts)
        db.commit()
    return True


def run_forever(worker_id: str | None = None) -> None:  # pragma: no cover - exercised manually
    worker_id = worker_id or f"worker-{uuid4().hex[:8]}"
    settings = get_settings()
    log.info("ingestion worker %s starting", worker_id)
    session_factory = get_sessionmaker()
    while True:
        with session_factory() as db:
            try:
                worked = process_one(db, worker_id)
            except Exception:
                log.exception("worker loop iteration failed")
                worked = False
        if not worked:
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    run_forever()
