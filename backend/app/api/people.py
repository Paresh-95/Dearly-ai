import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.personas import get_persona_or_404
from app.core.deps import get_current_user
from app.db.models import Person
from app.db.session import get_db

router = APIRouter(
    prefix="/personas/{persona_id}/people", tags=["people"], dependencies=[Depends(get_current_user)]
)

_MAX_NOTES_LEN = 4000


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    relation_to_persona: str = Field(default="", max_length=200)
    relation_to_user: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=_MAX_NOTES_LEN)


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    relation_to_persona: str | None = Field(default=None, max_length=200)
    relation_to_user: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=_MAX_NOTES_LEN)


class PersonOut(BaseModel):
    id: uuid.UUID
    name: str
    relation_to_persona: str
    relation_to_user: str
    notes: str

    class Config:
        from_attributes = True


@router.post("", response_model=PersonOut)
async def create_person(
    persona_id: uuid.UUID, payload: PersonCreate, db: AsyncSession = Depends(get_db)
) -> Person:
    persona = await get_persona_or_404(persona_id, db)

    person = Person(
        persona_id=persona.id,
        name=payload.name.strip(),
        relation_to_persona=payload.relation_to_persona.strip(),
        relation_to_user=payload.relation_to_user.strip(),
        notes=payload.notes.strip(),
    )
    db.add(person)
    await db.commit()
    await db.refresh(person)
    return person


@router.get("", response_model=list[PersonOut])
async def list_people(persona_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[Person]:
    await get_persona_or_404(persona_id, db)
    result = await db.execute(
        select(Person).where(Person.persona_id == persona_id).order_by(Person.created_at.desc())
    )
    return list(result.scalars().all())


@router.patch("/{person_id}", response_model=PersonOut)
async def update_person(
    persona_id: uuid.UUID, person_id: uuid.UUID, payload: PersonUpdate, db: AsyncSession = Depends(get_db)
) -> Person:
    await get_persona_or_404(persona_id, db)
    person = await db.get(Person, person_id)
    if person is None or person.persona_id != persona_id:
        raise HTTPException(status_code=404, detail="Person not found")

    if payload.name is not None:
        person.name = payload.name.strip()
    if payload.relation_to_persona is not None:
        person.relation_to_persona = payload.relation_to_persona.strip()
    if payload.relation_to_user is not None:
        person.relation_to_user = payload.relation_to_user.strip()
    if payload.notes is not None:
        person.notes = payload.notes.strip()

    await db.commit()
    await db.refresh(person)
    return person


@router.delete("/{person_id}", status_code=204)
async def delete_person(persona_id: uuid.UUID, person_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await get_persona_or_404(persona_id, db)
    person = await db.get(Person, person_id)
    if person is None or person.persona_id != persona_id:
        raise HTTPException(status_code=404, detail="Person not found")
    await db.delete(person)
    await db.commit()
