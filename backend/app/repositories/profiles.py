"""Profile data access. Every query is scoped to `user_id`; a profile owned by someone
else is indistinguishable from a missing one."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PersonProfile
from app.schemas.profile import ProfileCreate, ProfileUpdate


def list_for_user(db: Session, user_id: UUID) -> list[PersonProfile]:
    stmt = (
        select(PersonProfile)
        .where(PersonProfile.user_id == user_id)
        .order_by(PersonProfile.created_at)
    )
    return list(db.scalars(stmt))


def get_owned(db: Session, user_id: UUID, profile_id: UUID) -> PersonProfile | None:
    return db.scalar(
        select(PersonProfile).where(
            PersonProfile.id == profile_id, PersonProfile.user_id == user_id
        )
    )


def create(db: Session, user_id: UUID, data: ProfileCreate) -> PersonProfile:
    profile = PersonProfile(user_id=user_id, **data.model_dump())
    db.add(profile)
    db.flush()
    return profile


def update(db: Session, profile: PersonProfile, data: ProfileUpdate) -> PersonProfile:
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field in {"name", "relationship"}:
            continue  # required columns cannot be nulled
        if value is None and field in {
            "languages", "favourite_expressions", "hobbies", "important_relationships"
        }:
            continue
        setattr(profile, field, value)
    db.flush()
    return profile
