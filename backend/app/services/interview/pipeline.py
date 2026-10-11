"""The AI Memory Interviewer (brief §3 Method D): a guided conversation that proposes
candidate memories for review at the end, never saving anything the user hasn't approved.

Reuses almost everything already built: `conversations`/`messages` (kind=interview),
Milestone 3's `MemoryCandidateExtractor` for turning the transcript into candidates, and
the existing review/library UI for approving them — a completed interview's candidates are
ordinary `origin=interview` memories and need no new review surface."""

import hashlib
from collections.abc import Callable
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.domain.enums import ConversationKind, MemoryOrigin, MessageRole, Provenance, SourceKind
from app.models import Conversation, Memory, PersonProfile
from app.repositories import conversations as conversations_repo
from app.repositories import memories as memories_repo
from app.repositories import messages as messages_repo
from app.repositories import sources as sources_repo
from app.services.extraction.base import Segment
from app.services.providers.errors import ProviderNotConfigured
from app.services.providers.generation import ConversationTurn
from app.services.providers.interview import (
    InterviewerQuestionGenerator,
    get_interviewer_question_generator,
)
from app.services.providers.llm import MemoryCandidateExtractor, get_candidate_extractor

MAX_HISTORY_TURNS = 20
GENERATOR_UNAVAILABLE_MESSAGE = (
    "I can't continue the interview right now because the AI service isn't configured. "
    "You can still finish and review whatever has been shared so far."
)


def _opening_question(profile: PersonProfile) -> str:
    display_name = profile.preferred_name or profile.name
    return f"What's one of your happiest memories with {display_name}?"


def _history_turns(db: Session, conversation_id: UUID) -> list[ConversationTurn]:
    messages = messages_repo.recent_history(db, conversation_id, limit=MAX_HISTORY_TURNS)
    return [ConversationTurn(role=m.role, content=m.content) for m in messages]


def start_interview(db: Session, *, user_id: UUID, profile: PersonProfile) -> Conversation:
    conversation = conversations_repo.create(
        db, user_id, profile.id, kind=ConversationKind.INTERVIEW
    )
    messages_repo.create(
        db,
        user_id,
        profile.id,
        conversation.id,
        role=MessageRole.ASSISTANT,
        content=_opening_question(profile),
        diagnostics={"done": False},
    )
    db.flush()
    return conversation


def continue_interview(
    db: Session,
    *,
    user_id: UUID,
    conversation: Conversation,
    profile: PersonProfile,
    answer: str,
    get_generator: Callable[[], InterviewerQuestionGenerator] | None = None,
):
    messages_repo.create(
        db, user_id, profile.id, conversation.id, role=MessageRole.USER, content=answer
    )
    db.flush()
    history = _history_turns(db, conversation.id)  # includes the answer just stored

    display_name = profile.preferred_name or profile.name
    try:
        generator = (get_generator or get_interviewer_question_generator)()
        turn = generator.next_turn(
            display_name=display_name, relationship=profile.relationship, history=history
        )
    except ProviderNotConfigured as exc:
        return messages_repo.create(
            db,
            user_id,
            profile.id,
            conversation.id,
            role=MessageRole.ASSISTANT,
            content=GENERATOR_UNAVAILABLE_MESSAGE,
            diagnostics={"done": True, "generator_error": str(exc)},
        )

    if turn.done or not turn.question:
        content = turn.closing_message or "Thank you for sharing these memories."
        return messages_repo.create(
            db,
            user_id,
            profile.id,
            conversation.id,
            role=MessageRole.ASSISTANT,
            content=content,
            diagnostics={"done": True},
        )

    return messages_repo.create(
        db,
        user_id,
        profile.id,
        conversation.id,
        role=MessageRole.ASSISTANT,
        content=turn.question,
        diagnostics={"done": False},
    )


def _transcript_segments(db: Session, conversation_id: UUID) -> list[Segment]:
    """One segment per answer, paired with the question it answered for context — never
    the questions alone, since a question with no answer has nothing to extract."""
    messages = messages_repo.list_for_conversation(db, conversation_id, limit=200)
    segments: list[Segment] = []
    pending_question: str | None = None
    for m in messages:
        if m.role == MessageRole.ASSISTANT:
            pending_question = m.content
        elif m.role == MessageRole.USER:
            text = f"Q: {pending_question}\nA: {m.content}" if pending_question else m.content
            segments.append(Segment(text=text))
            pending_question = None
    return segments


def complete_interview(
    db: Session,
    *,
    user_id: UUID,
    conversation: Conversation,
    profile: PersonProfile,
    get_extractor: Callable[[], MemoryCandidateExtractor] | None = None,
) -> list[Memory]:
    """Idempotent: calling this twice on the same interview raises Conflict rather than
    creating duplicate candidates a second time (detected by the transcript Source already
    existing for this conversation)."""
    if sources_repo.get_by_conversation(db, conversation.id) is not None:
        raise Conflict("This interview has already been completed.")

    segments = _transcript_segments(db, conversation.id)
    if not segments:
        raise Conflict("There's nothing to extract yet — answer at least one question first.")

    # Call the extractor before writing anything: if no provider is configured, nothing is
    # persisted, so get_by_conversation's idempotency check above still sees "not completed"
    # and this can simply be retried later once a provider is configured.
    extractor = (get_extractor or get_candidate_extractor)()
    candidates = extractor.extract(
        segments=segments, profile_context=f"{profile.name} ({profile.relationship})"
    )

    transcript_hash = hashlib.sha256("\n".join(s.text for s in segments).encode()).hexdigest()
    source = sources_repo.create(
        db,
        user_id,
        profile.id,
        id=uuid4(),
        kind=SourceKind.INTERVIEW,
        provenance=Provenance.FAMILY_RECOLLECTION,
        filename=None,
        content_type=None,
        sha256=transcript_hash,
    )
    sources_repo.merge_metadata(db, source, {"conversation_id": str(conversation.id)})
    segment_rows = sources_repo.replace_segments(db, source, segments)
    db.flush()

    segments_by_ordinal = {i + 1: row for i, row in enumerate(segment_rows)}
    memories = [
        memories_repo.create_from_candidate(
            db,
            user_id,
            profile.id,
            source.id,
            candidate,
            segments_by_ordinal,
            origin=MemoryOrigin.INTERVIEW,
            provenance=Provenance.FAMILY_RECOLLECTION,
        )
        for candidate in candidates
    ]
    db.flush()
    return memories
