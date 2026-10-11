from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MessageRole
from app.models import Memory, Message


def create(
    db: Session,
    user_id: UUID,
    person_profile_id: UUID,
    conversation_id: UUID,
    *,
    role: MessageRole,
    content: str,
    cited_memory_ids: list[UUID] | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> Message:
    # created_at is set here, not left to the column's server_default: Postgres's now()
    # returns the same value for every statement in one transaction, and a single chat turn
    # inserts the user's message and the assistant's reply in the same transaction -- a
    # server-side default would tie them, making ordering (and recent_history, below)
    # unreliable.
    message = Message(
        user_id=user_id,
        person_profile_id=person_profile_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        cited_memory_ids=[str(mid) for mid in (cited_memory_ids or [])],
        diagnostics=diagnostics or {},
        created_at=datetime.now(UTC),
    )
    db.add(message)
    db.flush()
    return message


def list_for_conversation(db: Session, conversation_id: UUID, *, limit: int = 50) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
        .limit(limit)
    )
    return list(db.scalars(stmt))


def recent_history(db: Session, conversation_id: UUID, *, limit: int = 6) -> list[Message]:
    """The most recent `limit` messages, oldest first (ready to drop straight into a
    prompt) — used as conversation context, not the full transcript."""
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    return list(reversed(list(db.scalars(stmt))))


def resolve_cited_memories(db: Session, cited_memory_ids: list[str]) -> list[Memory]:
    """Missing ids (e.g. a since-deleted memory) are silently dropped — the UI treats a
    missing citation as "no longer available", not an error (see the Message model)."""
    if not cited_memory_ids:
        return []
    ids = [UUID(mid) for mid in cited_memory_ids]
    rows = {m.id: m for m in db.scalars(select(Memory).where(Memory.id.in_(ids)))}
    return [rows[i] for i in ids if i in rows]
