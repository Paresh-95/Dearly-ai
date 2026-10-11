from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import Auth, DbSession, OwnedConversation
from app.core.errors import NotFound
from app.models import Message
from app.repositories import conversations as conversations_repo
from app.repositories import messages as messages_repo
from app.repositories import profiles as profile_repo
from app.schemas.conversation import (
    CitedMemory,
    ConversationCreate,
    ConversationList,
    ConversationRead,
    MessageCreate,
    MessageList,
    MessageRead,
)
from app.services.generation import pipeline

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _to_message_read(db: DbSession, message: Message) -> MessageRead:
    cited = messages_repo.resolve_cited_memories(db, message.cited_memory_ids)
    return MessageRead(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        cited_memories=[
            CitedMemory(memory_id=m.id, title=m.title, category=m.category, provenance=m.provenance)
            for m in cited
        ],
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ConversationRead)
def create_conversation(body: ConversationCreate, db: DbSession, auth: Auth) -> ConversationRead:
    if profile_repo.get_owned(db, auth.user_id, body.person_profile_id) is None:
        raise NotFound("Profile not found")
    conversation = conversations_repo.create(
        db, auth.user_id, body.person_profile_id, title=body.title
    )
    db.commit()
    return ConversationRead.model_validate(conversation)


@router.get("", response_model=ConversationList)
def list_conversations(
    db: DbSession, auth: Auth, person_profile_id: UUID | None = None
) -> ConversationList:
    items = conversations_repo.list_for_user(db, auth.user_id, person_profile_id=person_profile_id)
    return ConversationList(items=[ConversationRead.model_validate(c) for c in items])


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation: OwnedConversation) -> ConversationRead:
    return ConversationRead.model_validate(conversation)


@router.get("/{conversation_id}/messages", response_model=MessageList)
def list_messages(conversation: OwnedConversation, db: DbSession) -> MessageList:
    messages = messages_repo.list_for_conversation(db, conversation.id, limit=200)
    return MessageList(items=[_to_message_read(db, m) for m in messages])


@router.post(
    "/{conversation_id}/messages", status_code=status.HTTP_201_CREATED, response_model=MessageRead
)
def send_message(
    conversation: OwnedConversation, body: MessageCreate, db: DbSession, auth: Auth
) -> MessageRead:
    profile = profile_repo.get_owned(db, auth.user_id, conversation.person_profile_id)
    if profile is None:
        raise NotFound("Profile not found")
    assistant_message = pipeline.answer_question(
        db,
        user_id=auth.user_id,
        conversation=conversation,
        profile=profile,
        question=body.content,
    )
    db.commit()
    return _to_message_read(db, assistant_message)
