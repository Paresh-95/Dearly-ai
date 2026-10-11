from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import JobState, Provenance, SourceKind
from app.models._helpers import enum_check, profile_fk


class Source(IdMixin, TimestampMixin, Base):
    """An uploaded file, recording, chat export or manual entry. The original is stored
    untouched in private object storage under `storage_key`."""

    __tablename__ = "sources"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    provenance: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=Provenance.UNKNOWN.value
    )
    filename: Mapped[str | None] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(200))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    storage_key: Mapped[str | None] = mapped_column(String(512))
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        profile_fk(),
        UniqueConstraint("id", "person_profile_id", name="uq_sources_id_person_profile_id"),
        enum_check("kind", SourceKind),
        enum_check("provenance", Provenance),
        Index("ix_sources_person_profile_id", "person_profile_id"),
    )


class SourceSegment(IdMixin, Base):
    """An extracted passage with provenance. `raw_text` is exactly what the extractor
    produced; `normalized_text` is a cleaned copy and is never a replacement for it."""

    __tablename__ = "source_segments"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    t_start_ms: Mapped[int | None] = mapped_column(Integer)
    t_end_ms: Mapped[int | None] = mapped_column(Integer)
    speaker_label: Mapped[str | None] = mapped_column(String(200))
    # Diarisation labels are never treated as identity unless a human confirms.
    speaker_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    __table_args__ = (
        profile_fk(),
        ForeignKeyConstraint(
            ["source_id", "person_profile_id"],
            ["sources.id", "sources.person_profile_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("source_id", "ordinal", name="uq_source_segments_source_id_ordinal"),
        CheckConstraint(
            "t_end_ms IS NULL OR t_start_ms IS NULL OR t_end_ms >= t_start_ms",
            name="time_range_valid",
        ),
        CheckConstraint(
            "char_end IS NULL OR char_start IS NULL OR char_end >= char_start",
            name="char_range_valid",
        ),
    )


class IngestionJob(IdMixin, TimestampMixin, Base):
    """Postgres-backed work queue row. `progress` is NULL unless a stage can report a
    real value, so the UI never shows invented progress."""

    __tablename__ = "ingestion_jobs"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=JobState.QUEUED.value
    )
    stage: Mapped[str | None] = mapped_column(String(50))
    progress: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    error: Mapped[str | None] = mapped_column(Text)
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(100))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        profile_fk(),
        enum_check("state", JobState),
        CheckConstraint("progress IS NULL OR progress BETWEEN 0 AND 100", name="progress_range"),
        Index("ix_ingestion_jobs_claim", "state", "run_after"),
        Index("ix_ingestion_jobs_person_profile_id", "person_profile_id"),
    )
