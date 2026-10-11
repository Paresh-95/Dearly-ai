from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.enums import JobState, Provenance, SourceKind


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_profile_id: UUID
    kind: SourceKind
    provenance: Provenance
    filename: str | None
    content_type: str | None
    size_bytes: int | None
    created_at: datetime


class SourceList(BaseModel):
    items: list[SourceRead]


class SourceSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ordinal: int
    raw_text: str
    page: int | None
    char_start: int | None
    char_end: int | None
    t_start_ms: int | None
    t_end_ms: int | None
    speaker_label: str | None
    speaker_verified: bool


class SourceSegmentList(BaseModel):
    items: list[SourceSegmentRead]


class IngestionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    person_profile_id: UUID
    state: JobState
    stage: str | None
    progress: int | None
    attempts: int
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class IngestionJobList(BaseModel):
    items: list[IngestionJobRead]
