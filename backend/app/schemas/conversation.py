from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ConversationKind, MessageRole


class ConversationCreate(BaseModel):
    person_profile_id: UUID
    title: str | None = Field(default=None, max_length=300)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_profile_id: UUID
    kind: ConversationKind
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationList(BaseModel):
    items: list[ConversationRead]


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CitedMemory(BaseModel):
    """Enough for the UI to show "sourced from: <title>" and link to it — never the raw
    developer diagnostics the pipeline also records."""

    memory_id: UUID
    title: str
    category: str | None
    provenance: str


class MessageRead(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    cited_memories: list[CitedMemory]
    created_at: datetime


class MessageList(BaseModel):
    items: list[MessageRead]
