from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.domain.enums import ConsentType, ConversationKind, MessageRole
from app.models._helpers import enum_check, profile_fk


class Conversation(IdMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=ConversationKind.ASK.value
    )
    title: Mapped[str | None] = mapped_column(String(300))

    __table_args__ = (
        profile_fk(),
        enum_check("kind", ConversationKind),
        Index("ix_conversations_person_profile_id", "person_profile_id"),
    )


class Message(IdMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # IDs of memories the assistant relied on. Not FKs: a deleted memory must not
    # delete conversation history, but the UI treats missing IDs as "removed".
    cited_memory_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(String(36)), nullable=False, server_default=text("'{}'")
    )
    # Developer-facing only; never rendered to the user.
    diagnostics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        profile_fk(),
        enum_check("role", MessageRole),
        Index("ix_messages_conversation_id", "conversation_id", "created_at"),
    )


class Feedback(IdMixin, TimestampMixin, Base):
    __tablename__ = "feedback"

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    person_profile_id: Mapped[UUID] = mapped_column(nullable=False)
    message_id: Mapped[UUID | None] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    memory_id: Mapped[UUID | None] = mapped_column(ForeignKey("memories.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        profile_fk(),
        CheckConstraint(
            "message_id IS NOT NULL OR memory_id IS NOT NULL", name="has_target"
        ),
        Index("ix_feedback_person_profile_id", "person_profile_id"),
    )


class ConsentRecord(IdMixin, TimestampMixin, Base):
    """Append-only log of consent decisions. A later row supersedes an earlier one."""

    __tablename__ = "consent_records"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # NULL = account-level consent; set = consent for one profile.
    person_profile_id: Mapped[UUID | None] = mapped_column()
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    granted: Mapped[bool] = mapped_column(nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["person_profile_id", "user_id"],
            ["person_profiles.id", "person_profiles.user_id"],
            ondelete="CASCADE",
        ),
        enum_check("consent_type", ConsentType),
    )
