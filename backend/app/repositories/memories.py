"""Memory data access. Every query is scoped to `user_id` directly (each table carries its
own owner column, no joins needed) — see `docs/architecture/blueprint.md` A7.

No ORM `relationship()` is declared on the models (consistent with the rest of the schema,
which relies on plain columns plus DB-level FKs/cascades). `people` is loaded with a separate
batched query and attached as a plain, unmapped attribute so `MemoryRead.model_validate` can
read it."""

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.api.pagination import decode_cursor, encode_cursor
from app.core.errors import Conflict
from app.domain.enums import MemoryOrigin, MemoryStatus, Provenance
from app.domain.memory_rules import (
    InvalidTransition,
    ensure_transition_allowed,
    next_status_on_update,
)
from app.models import Feedback, Memory, MemoryPerson, MemorySource, SourceSegment
from app.repositories import memory_chunks as chunks_repo
from app.schemas.extraction import MemoryCandidate
from app.schemas.memory import MemoryCreate, MemoryUpdate


def _attach_people(db: Session, memories: Iterable[Memory]) -> None:
    memories = list(memories)
    if not memories:
        return
    ids = [m.id for m in memories]
    rows = db.scalars(
        select(MemoryPerson).where(MemoryPerson.memory_id.in_(ids)).order_by(MemoryPerson.id)
    )
    by_memory: dict[UUID, list[MemoryPerson]] = {m.id: [] for m in memories}
    for row in rows:
        by_memory[row.memory_id].append(row)
    for m in memories:
        m.people = by_memory[m.id]  # type: ignore[attr-defined]  (unmapped, for serialization only)


def get_owned(db: Session, user_id: UUID, memory_id: UUID) -> Memory | None:
    memory = db.scalar(select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id))
    if memory is not None:
        _attach_people(db, [memory])
    return memory


def list_for_user(
    db: Session,
    user_id: UUID,
    *,
    person_profile_id: UUID | None = None,
    status: MemoryStatus | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> tuple[list[Memory], str | None, int]:
    """Returns (items, next_cursor, total_matching_filter). `q` is a plain substring filter
    over title/description for the library view — not the semantic/hybrid RAG search built
    in Milestone 5."""
    filters = [Memory.user_id == user_id]
    if person_profile_id is not None:
        filters.append(Memory.person_profile_id == person_profile_id)
    if status is not None:
        filters.append(Memory.status == status)
    if category is not None:
        filters.append(Memory.category == category)
    if q:
        like = f"%{q}%"
        filters.append((Memory.title.ilike(like)) | (Memory.description.ilike(like)))

    total = db.scalar(select(func.count()).select_from(Memory).where(*filters)) or 0

    stmt = select(Memory).where(*filters)
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)
        stmt = stmt.where(tuple_(Memory.created_at, Memory.id) > tuple_(cursor_ts, cursor_id))
    stmt = stmt.order_by(Memory.created_at, Memory.id).limit(limit + 1)

    items = list(db.scalars(stmt))
    next_cursor = None
    if len(items) > limit:
        items = items[:limit]
        last = items[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    _attach_people(db, items)
    return items, next_cursor, total


def _replace_people(db: Session, memory: Memory, people: list) -> None:  # noqa: ANN001
    db.query(MemoryPerson).filter(MemoryPerson.memory_id == memory.id).delete()
    for p in people:
        db.add(
            MemoryPerson(
                user_id=memory.user_id,
                person_profile_id=memory.person_profile_id,
                memory_id=memory.id,
                name=p.name,
                relationship=p.relationship,
            )
        )


def create(db: Session, user_id: UUID, data: MemoryCreate) -> Memory:
    memory = Memory(
        user_id=user_id,
        person_profile_id=data.person_profile_id,
        title=data.title,
        description=data.description,
        status=data.status,
        # Manual entries are always self-authored and have no recording evidence; a user
        # cannot claim "direct recording" provenance by typing a memory in by hand.
        origin=MemoryOrigin.USER_WRITTEN,
        provenance=Provenance.FAMILY_RECOLLECTION,
        category=data.category,
        date_text=data.date_text,
        date_start=data.date_start,
        date_end=data.date_end,
        location=data.location,
        approved_at=datetime.now(UTC) if data.status == MemoryStatus.APPROVED else None,
    )
    db.add(memory)
    db.flush()
    _replace_people(db, memory, data.people)
    db.flush()
    _attach_people(db, [memory])
    return memory


def update(db: Session, memory: Memory, data: MemoryUpdate) -> Memory:
    payload = data.model_dump(exclude_unset=True, exclude={"status", "people"})
    requested_status = data.status if "status" in data.model_fields_set else None
    # Keep the original MemoryPersonInput objects (not the dict form `model_dump` would give)
    # so `_replace_people` can read `.name`/`.relationship` attributes.
    people = data.people if "people" in data.model_fields_set else None

    changed_fields = {k for k, v in payload.items() if getattr(memory, k) != v}
    if people is not None:
        changed_fields.add("people")

    target_status = next_status_on_update(
        memory.status, requested_status=requested_status, changed_fields=changed_fields
    )
    try:
        ensure_transition_allowed(memory.status, target_status)
    except InvalidTransition as exc:
        raise Conflict(str(exc)) from exc
    was_approved = memory.status == MemoryStatus.APPROVED

    for field, value in payload.items():
        setattr(memory, field, value)
    if people is not None:
        _replace_people(db, memory, people)
    memory.status = target_status
    memory.approved_at = datetime.now(UTC) if target_status == MemoryStatus.APPROVED else None

    db.flush()
    if was_approved and target_status != MemoryStatus.APPROVED:
        # Leaving `approved`: the indexed content is no longer current/trusted, so it must
        # not stay searchable. Re-approving later re-chunks and re-embeds from scratch.
        chunks_repo.clear_chunks(db, memory.id)
    _attach_people(db, [memory])
    return memory


def create_from_candidate(
    db: Session,
    user_id: UUID,
    person_profile_id: UUID,
    source_id: UUID,
    candidate: MemoryCandidate,
    segments_by_ordinal: dict[int, SourceSegment],
) -> Memory:
    """Writes one LLM-proposed candidate as an `awaiting_review` memory with `origin=
    extracted`, linking it back to the exact passages it was drawn from. Confidence below
    0.6 is surfaced as `is_uncertain` so the review queue flags it without the reviewer
    having to open each one to find out."""
    memory = Memory(
        user_id=user_id,
        person_profile_id=person_profile_id,
        title=candidate.title,
        description=candidate.description,
        status=MemoryStatus.AWAITING_REVIEW,
        origin=MemoryOrigin.EXTRACTED,
        provenance=Provenance.DOCUMENT,
        category=candidate.category,
        date_text=candidate.date_text,
        location=candidate.location,
        confidence=candidate.confidence,
        is_uncertain=candidate.confidence < 0.6,
        uncertainty_note=candidate.uncertainty_note,
        quotations=[{"text": q} for q in candidate.quotations],
    )
    db.add(memory)
    db.flush()

    for p in candidate.people:
        db.add(
            MemoryPerson(
                user_id=user_id,
                person_profile_id=person_profile_id,
                memory_id=memory.id,
                name=p.name,
                relationship=p.relationship,
            )
        )

    linked_segments = {
        segments_by_ordinal[o]
        for o in candidate.supporting_segment_ordinals
        if o in segments_by_ordinal
    }
    for seg in linked_segments:
        db.add(
            MemorySource(
                user_id=user_id,
                person_profile_id=person_profile_id,
                memory_id=memory.id,
                source_id=source_id,
                segment_id=seg.id,
            )
        )
    if not linked_segments:
        # No valid ordinal came back from the model; still record provenance at the
        # source level so "view original source" has somewhere to point.
        db.add(
            MemorySource(
                user_id=user_id,
                person_profile_id=person_profile_id,
                memory_id=memory.id,
                source_id=source_id,
            )
        )

    db.flush()
    _attach_people(db, [memory])
    return memory


def approve(db: Session, memory: Memory) -> Memory:
    try:
        ensure_transition_allowed(memory.status, MemoryStatus.APPROVED)
    except InvalidTransition as exc:
        raise Conflict(str(exc)) from exc
    memory.status = MemoryStatus.APPROVED
    memory.approved_at = datetime.now(UTC)
    db.flush()
    chunks_repo.reindex_memory(db, memory)
    _attach_people(db, [memory])
    return memory


def reject(db: Session, memory: Memory, note: str | None) -> Memory:
    try:
        ensure_transition_allowed(memory.status, MemoryStatus.REJECTED)
    except InvalidTransition as exc:
        raise Conflict(str(exc)) from exc
    was_approved = memory.status == MemoryStatus.APPROVED
    memory.status = MemoryStatus.REJECTED
    memory.approved_at = None
    if was_approved:
        chunks_repo.clear_chunks(db, memory.id)
    if note:
        db.add(
            Feedback(
                user_id=memory.user_id,
                person_profile_id=memory.person_profile_id,
                memory_id=memory.id,
                kind="memory_rejected",
                note=note,
            )
        )
    db.flush()
    _attach_people(db, [memory])
    return memory


def delete(db: Session, memory: Memory) -> None:
    db.delete(memory)
    db.flush()
