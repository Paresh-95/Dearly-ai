"""`InterviewTurn` is the structured-output contract between the interviewer's question
generator and the interview pipeline — not a public API schema. The `*Read`/`*Create`
schemas below it are the public API schemas for the /interviews endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import MessageRole
from app.schemas.memory import MemoryRead


class InterviewTurn(BaseModel):
    question: str | None = Field(default=None, max_length=500)
    done: bool = False
    closing_message: str | None = Field(default=None, max_length=1000)


class InterviewCreate(BaseModel):
    person_profile_id: UUID


class InterviewMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class InterviewMessageRead(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    done: bool
    created_at: datetime


class InterviewStartResponse(BaseModel):
    conversation_id: UUID
    message: InterviewMessageRead


class InterviewCompleteResponse(BaseModel):
    candidates: list[MemoryRead]
