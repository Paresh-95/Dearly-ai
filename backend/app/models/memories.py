from datetime import date, datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import IndexStatus, MemoryOrigin, MemoryStatus, Provenance
from app.models._helpers import enum_check, profile_fk

EMBEDDING_DIM = get_settings().embedding_dim


class Memory(IdMixin, TimestampMixin, Base):
    """A structured memory. `description` keeps the user's original wording; edits are
    explicit updates, never silent rewrites. Only `approved` memories are indexed."""

    __tablename__ = "memories"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=MemoryStatus.DRAFT.value
    )
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    provenance: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=Provenance.UNKNOWN.value
    )
    category: Mapped[str | None] = mapped_column(String(100))
    date_text: Mapped[str | None] = mapped_column(String(200))  # as the user wrote it
    date_start: Mapped[date | None] = mapped_column()
    date_end: Mapped[date | None] = mapped_column()
    location: Mapped[str | None] = mapped_column(String(300))
    is_uncertain: Mapped[bool] = mapped_column(nullable=False, server_default=sql_text("false"))
    uncertainty_note: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    quotations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=sql_text("'[]'::jsonb")
    )
    personality_attributes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=sql_text("'{}'")
    )
    communication_patterns: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=sql_text("'{}'")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        profile_fk(),
        UniqueConstraint("id", "person_profile_id", name="uq_memories_id_person_profile_id"),
        enum_check("status", MemoryStatus),
        enum_check("origin", MemoryOrigin),
        enum_check("provenance", Provenance),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_range"
        ),
        CheckConstraint(
            "(status = 'approved') = (approved_at IS NOT NULL)", name="approved_at_matches_status"
        ),
        Index("ix_memories_profile_status", "person_profile_id", "status"),
    )


class MemoryPerson(IdMixin, Base):
    """A person mentioned in a memory (free text; not necessarily a profile)."""

    __tablename__ = "memory_people"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    memory_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
        profile_fk(),
        ForeignKeyConstraint(
            ["memory_id", "person_profile_id"],
            ["memories.id", "memories.person_profile_id"],
            ondelete="CASCADE",
        ),
        Index("ix_memory_people_memory_id", "memory_id"),
    )


class MemorySource(IdMixin, Base):
    """Evidence link from a memory to a source (and optionally a specific segment)."""

    __tablename__ = "memory_sources"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    memory_id: Mapped[UUID] = mapped_column(nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False)
    segment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("source_segments.id", ondelete="SET NULL")
    )
    quote_span: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    __table_args__ = (
        profile_fk(),
        ForeignKeyConstraint(
            ["memory_id", "person_profile_id"],
            ["memories.id", "memories.person_profile_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["source_id", "person_profile_id"],
            ["sources.id", "sources.person_profile_id"],
            ondelete="CASCADE",
        ),
        Index("ix_memory_sources_memory_id", "memory_id"),
        Index("ix_memory_sources_source_id", "source_id"),
    )


class MemoryChunk(IdMixin, TimestampMixin, Base):
    """Searchable unit derived from an approved memory; carries its embedding and
    full-text vector. Deleted with its memory (FK cascade)."""

    __tablename__ = "memory_chunks"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    memory_id: Mapped[UUID] = mapped_column(nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    index_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=IndexStatus.PENDING.value
    )
    # 'simple' config: no language-specific stemming, safe for mixed-language memories.
    tsv: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', text)", persisted=True)
    )
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=sql_text("'{}'::jsonb")
    )

    __table_args__ = (
        profile_fk(),
        ForeignKeyConstraint(
            ["memory_id", "person_profile_id"],
            ["memories.id", "memories.person_profile_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("memory_id", "chunk_index", name="uq_memory_chunks_memory_id_chunk_index"),
        UniqueConstraint(
            "person_profile_id", "content_hash", name="uq_memory_chunks_profile_content_hash"
        ),
        enum_check("index_status", IndexStatus),
        CheckConstraint(
            "(index_status = 'indexed') = (embedding IS NOT NULL)",
            name="indexed_has_embedding",
        ),
        Index("ix_memory_chunks_tsv", "tsv", postgresql_using="gin"),
        Index(
            "ix_memory_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_memory_chunks_profile", "person_profile_id"),
    )
