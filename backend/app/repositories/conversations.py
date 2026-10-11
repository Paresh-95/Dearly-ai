from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ConversationKind
from app.models import Conversation


def create(
    db: Session,
    user_id: UUID,
    person_profile_id: UUID,
    *,
    kind: ConversationKind = ConversationKind.ASK,
    title: str | None = None,
) -> Conversation:
    conversation = Conversation(
        user_id=user_id,
        person_profile_id=person_profile_id,
        kind=kind,
        title=title,
    )
    db.add(conversation)
    db.flush()
    return conversation


def get_owned(
    db: Session, user_id: UUID, conversation_id: UUID, *, kind: ConversationKind | None = None
) -> Conversation | None:
    filters = [Conversation.id == conversation_id, Conversation.user_id == user_id]
    if kind is not None:
        filters.append(Conversation.kind == kind)
    return db.scalar(select(Conversation).where(*filters))


def list_for_user(
    db: Session,
    user_id: UUID,
    *,
    person_profile_id: UUID | None = None,
    kind: ConversationKind | None = None,
) -> list[Conversation]:
    stmt = select(Conversation).where(Conversation.user_id == user_id)
    if person_profile_id is not None:
        stmt = stmt.where(Conversation.person_profile_id == person_profile_id)
    if kind is not None:
        stmt = stmt.where(Conversation.kind == kind)
    return list(db.scalars(stmt.order_by(Conversation.created_at.desc())))
