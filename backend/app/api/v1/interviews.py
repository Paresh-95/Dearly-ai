from fastapi import APIRouter, status

from app.api.deps import Auth, DbSession, OwnedInterview
from app.core.errors import NotFound, ServiceUnavailable
from app.models import Message
from app.repositories import messages as messages_repo
from app.repositories import profiles as profile_repo
from app.schemas.interview import (
    InterviewCompleteResponse,
    InterviewCreate,
    InterviewMessageCreate,
    InterviewMessageRead,
    InterviewStartResponse,
)
from app.schemas.memory import MemoryRead
from app.services.interview import pipeline
from app.services.providers.errors import ProviderNotConfigured

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _to_turn_read(message: Message) -> InterviewMessageRead:
    return InterviewMessageRead(
        id=message.id,
        role=message.role,
        content=message.content,
        done=bool(message.diagnostics.get("done")),
        created_at=message.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InterviewStartResponse)
def start_interview(body: InterviewCreate, db: DbSession, auth: Auth) -> InterviewStartResponse:
    profile = profile_repo.get_owned(db, auth.user_id, body.person_profile_id)
    if profile is None:
        raise NotFound("Profile not found")
    conversation = pipeline.start_interview(db, user_id=auth.user_id, profile=profile)
    db.commit()
    first_message = messages_repo.list_for_conversation(db, conversation.id, limit=1)[0]
    return InterviewStartResponse(
        conversation_id=conversation.id, message=_to_turn_read(first_message)
    )


@router.post("/{interview_id}/messages", response_model=InterviewMessageRead)
def send_interview_answer(
    interview: OwnedInterview, body: InterviewMessageCreate, db: DbSession, auth: Auth
) -> InterviewMessageRead:
    profile = profile_repo.get_owned(db, auth.user_id, interview.person_profile_id)
    if profile is None:
        raise NotFound("Profile not found")
    message = pipeline.continue_interview(
        db, user_id=auth.user_id, conversation=interview, profile=profile, answer=body.content
    )
    db.commit()
    return _to_turn_read(message)


@router.post("/{interview_id}/complete", response_model=InterviewCompleteResponse)
def complete_interview(
    interview: OwnedInterview, db: DbSession, auth: Auth
) -> InterviewCompleteResponse:
    profile = profile_repo.get_owned(db, auth.user_id, interview.person_profile_id)
    if profile is None:
        raise NotFound("Profile not found")
    try:
        candidates = pipeline.complete_interview(
            db, user_id=auth.user_id, conversation=interview, profile=profile
        )
    except ProviderNotConfigured as exc:
        # Nothing was written (see pipeline.complete_interview's docstring), so this can
        # simply be retried once a provider is configured.
        raise ServiceUnavailable(str(exc)) from exc
    db.commit()
    return InterviewCompleteResponse(candidates=[MemoryRead.model_validate(m) for m in candidates])
