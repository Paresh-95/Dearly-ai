from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ConversationKind
from app.models import Conversation


def create(
    db: Session, user_id: UUID, person_profile_id: UUID, *, title: str | None = None
) -> Conversation:
    conversation = Conversation(
        user_id=user_id,
        person_profile_id=person_profile_id,
        kind=ConversationKind.ASK,
        title=title,
    )
    db.add(conversation)
    db.flush()
    return conversation


def get_owned(db: Session, user_id: UUID, conversation_id: UUID) -> Conversation | None:
    return db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        )
    )


def list_for_user(
    db: Session, user_id: UUID, *, person_profile_id: UUID | None = None
) -> list[Conversation]:
    stmt = select(Conversation).where(Conversation.user_id == user_id)
    if person_profile_id is not None:
        stmt = stmt.where(Conversation.person_profile_id == person_profile_id)
    return list(db.scalars(stmt.order_by(Conversation.created_at.desc())))
