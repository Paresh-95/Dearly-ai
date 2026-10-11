"""Consent records are append-only: a new row always supersedes an older one with the same
type/profile rather than overwriting it, preserving a full audit trail of what was agreed to
and when."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ConsentRecord
from app.schemas.consent import ConsentCreate


def create(db: Session, user_id: UUID, data: ConsentCreate) -> ConsentRecord:
    record = ConsentRecord(user_id=user_id, **data.model_dump())
    db.add(record)
    db.flush()
    return record


def list_for_user(
    db: Session, user_id: UUID, *, person_profile_id: UUID | None = None
) -> list[ConsentRecord]:
    stmt = select(ConsentRecord).where(ConsentRecord.user_id == user_id)
    if person_profile_id is not None:
        stmt = stmt.where(ConsentRecord.person_profile_id == person_profile_id)
    return list(db.scalars(stmt.order_by(ConsentRecord.created_at.desc())))


def latest_granted(
    db: Session, user_id: UUID, consent_type: str, *, person_profile_id: UUID | None = None
) -> ConsentRecord | None:
    """The most recent decision for a consent type, if the latest one was a grant."""
    stmt = (
        select(ConsentRecord)
        .where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.person_profile_id == person_profile_id,
        )
        .order_by(ConsentRecord.created_at.desc())
        .limit(1)
    )
    latest = db.scalar(stmt)
    return latest if latest and latest.granted else None
