import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    is_approved: Mapped[bool] = mapped_column(default=False)
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    relationship_to_user: Mapped[str] = mapped_column(String(200), default="")
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    user_relationship: Mapped[str] = mapped_column(String(200), default="")
    user_gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    personality_notes: Mapped[dict] = mapped_column(JSONB, default=dict)
    language: Mapped[str] = mapped_column(String(10), default="en")
    provider_voice_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sarvam_voice_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    voice_provider: Mapped[str] = mapped_column(String(20), default="fish_audio")
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memories: Mapped[list["Memory"]] = relationship(back_populates="persona", cascade="all, delete-orphan")
    voice_samples: Mapped[list["VoiceSample"]] = relationship(back_populates="persona", cascade="all, delete-orphan")
    people: Mapped[list["Person"]] = relationship(back_populates="persona", cascade="all, delete-orphan")


class Person(Base):
    """A structured entry for someone in the persona's life — their relation
    to the persona and to the user, kept separate from free-text Memory rows
    so relational questions ("who is X to me") can be answered by a direct
    name lookup instead of relying on semantic/vector search to surface a
    relationship fact buried in a story.
    """

    __tablename__ = "related_people"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    relation_to_persona: Mapped[str] = mapped_column(String(200), default="")
    relation_to_user: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    persona: Mapped[Persona] = relationship(back_populates="people")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(20))
    # story | fact | trait | quote | value | routine | preference |
    # physical_detail | advice | regret | timeline_event
    raw_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    persona: Mapped[Persona] = relationship(back_populates="memories")
    chunks: Mapped[list["MemoryChunk"]] = relationship(back_populates="memory", cascade="all, delete-orphan")


class MemoryChunk(Base):
    __tablename__ = "memory_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("memories.id", ondelete="CASCADE"))
    persona_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"))
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memory: Mapped[Memory] = relationship(back_populates="chunks")


class VoiceSample(Base):
    __tablename__ = "voice_samples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"))
    storage_path: Mapped[str] = mapped_column(String(500))
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    persona: Mapped[Persona] = relationship(back_populates="voice_samples")


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    turns: Mapped[list["ConversationTurn"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversation_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    text: Mapped[str] = mapped_column(Text)
    retrieved_memory_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[ConversationSession] = relationship(back_populates="turns")
