"""Orchestrates one turn of the Ask AI conversation: retrieve evidence (Milestone 5) ->
generate a grounded answer -> validate its citations against what was actually retrieved ->
persist both the user's question and the assistant's reply. Stops short of nothing: if
retrieval finds no evidence at all, the LLM is never called — there is nothing it could
honestly answer with, so a templated, zero-risk response is used instead."""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MessageRole
from app.models import Conversation, Memory, PersonProfile
from app.repositories import messages as messages_repo
from app.schemas.generation import GroundedAnswer
from app.services.providers.errors import ProviderNotConfigured
from app.services.providers.generation import (
    AnswerGenerator,
    ConversationTurn,
    EvidenceForPrompt,
    get_answer_generator,
)
from app.services.retrieval import pipeline as retrieval_pipeline

MAX_EVIDENCE = 6
MAX_HISTORY_TURNS = 6
NO_EVIDENCE_ANSWER = (
    "I couldn't find anything in the shared memories that answers this. "
    "You could try asking it a different way, or add a memory that covers it."
)
GENERATOR_UNAVAILABLE_ANSWER = (
    "I found some related memories, but I can't write an answer right now because the "
    "answer-writing service isn't configured. The memories themselves are still there to "
    "browse in the library."
)


def _persona_guidance(profile: PersonProfile) -> str:
    parts = []
    if profile.personality:
        parts.append(profile.personality[:600])
    if profile.biography:
        parts.append(profile.biography[:400])
    if profile.favourite_expressions:
        parts.append("Favourite expressions: " + ", ".join(profile.favourite_expressions[:10]))
    return " ".join(parts)


def _history_turns(db: Session, conversation_id: UUID) -> list[ConversationTurn]:
    messages = messages_repo.recent_history(db, conversation_id, limit=MAX_HISTORY_TURNS)
    return [ConversationTurn(role=m.role, content=m.content) for m in messages]


def answer_question(
    db: Session,
    *,
    user_id: UUID,
    conversation: Conversation,
    profile: PersonProfile,
    question: str,
    get_generator: Callable[[], AnswerGenerator] | None = None,
    search: Callable[..., tuple] | None = None,
):
    search_fn = search or retrieval_pipeline.search
    history = _history_turns(db, conversation.id)  # prior turns only, before this question

    messages_repo.create(
        db, user_id, profile.id, conversation.id, role=MessageRole.USER, content=question
    )
    db.flush()

    evidence_items, retrieval_diagnostics = search_fn(
        db, user_id=user_id, person_profile_id=profile.id, query=question, limit=MAX_EVIDENCE
    )

    if not evidence_items:
        return messages_repo.create(
            db,
            user_id,
            profile.id,
            conversation.id,
            role=MessageRole.ASSISTANT,
            content=NO_EVIDENCE_ANSWER,
            diagnostics={"evidence_count": 0, "retrieval": retrieval_diagnostics},
        )

    memory_ids = [i.memory_id for i in evidence_items]
    memory_rows = {m.id: m for m in db.scalars(select(Memory).where(Memory.id.in_(memory_ids)))}
    evidence = [
        EvidenceForPrompt(
            number=i + 1,
            memory_id=item.memory_id,
            text=item.text,
            provenance=memory_rows[item.memory_id].provenance
            if item.memory_id in memory_rows
            else "unknown",
        )
        for i, item in enumerate(evidence_items)
    ]

    display_name = profile.preferred_name or profile.name
    try:
        generator = (get_generator or get_answer_generator)()
        answer: GroundedAnswer = generator.generate(
            display_name=display_name,
            relationship=profile.relationship,
            persona_guidance=_persona_guidance(profile),
            evidence=evidence,
            history=history,
            question=question,
        )
    except ProviderNotConfigured as exc:
        return messages_repo.create(
            db,
            user_id,
            profile.id,
            conversation.id,
            role=MessageRole.ASSISTANT,
            content=GENERATOR_UNAVAILABLE_ANSWER,
            diagnostics={
                "evidence_count": len(evidence),
                "retrieval": retrieval_diagnostics,
                "generation_error": str(exc),
            },
        )

    by_number = {e.number: e.memory_id for e in evidence}
    cited_memory_ids = (
        [by_number[n] for n in answer.cited_evidence_numbers if n in by_number]
        if answer.has_sufficient_evidence
        else []
    )

    return messages_repo.create(
        db,
        user_id,
        profile.id,
        conversation.id,
        role=MessageRole.ASSISTANT,
        content=answer.answer,
        cited_memory_ids=cited_memory_ids,
        diagnostics={
            "evidence_count": len(evidence),
            "retrieval": retrieval_diagnostics,
            "has_sufficient_evidence": answer.has_sufficient_evidence,
            "conflict_detected": answer.conflict_detected,
            "conflict_note": answer.conflict_note,
        },
    )
