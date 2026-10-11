from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import MemoryStatus

# Only these two statuses may be requested through the generic update endpoint; moving to
# `approved` or `rejected` goes through the dedicated /approve and /reject actions so the
# bookkeeping (approved_at, rejection feedback) always happens together with the transition.
PatchableStatus = Literal[MemoryStatus.DRAFT, MemoryStatus.AWAITING_REVIEW]


class MemoryPersonInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    relationship: str | None = Field(default=None, max_length=100)


class MemoryPersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    relationship: str | None


def _check_dates(start: date | None, end: date | None) -> None:
    if start and end and end < start:
        raise ValueError("date_end cannot be before date_start")


class MemoryBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=20_000)
    category: str | None = Field(default=None, max_length=100)
    date_text: str | None = Field(default=None, max_length=200)
    date_start: date | None = None
    date_end: date | None = None
    location: str | None = Field(default=None, max_length=300)
    people: list[MemoryPersonInput] = Field(default_factory=list, max_length=50)


class MemoryCreate(MemoryBase):
    person_profile_id: UUID
    # Manual entries only save as a draft or go straight to the review queue; `approved` and
    # `rejected` are not creatable states (see PatchableStatus).
    status: PatchableStatus = MemoryStatus.DRAFT

    @model_validator(mode="after")
    def _dates(self) -> "MemoryCreate":
        _check_dates(self.date_start, self.date_end)
        return self


class MemoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, min_length=1, max_length=20_000)
    category: str | None = Field(default=None, max_length=100)
    date_text: str | None = Field(default=None, max_length=200)
    date_start: date | None = None
    date_end: date | None = None
    location: str | None = Field(default=None, max_length=300)
    people: list[MemoryPersonInput] | None = Field(default=None, max_length=50)
    is_uncertain: bool | None = None
    uncertainty_note: str | None = Field(default=None, max_length=2_000)
    status: PatchableStatus | None = None

    @model_validator(mode="after")
    def _dates(self) -> "MemoryUpdate":
        _check_dates(self.date_start, self.date_end)
        return self


class MemoryRejectRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2_000)


class MemoryRead(MemoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_profile_id: UUID
    status: MemoryStatus
    origin: str
    provenance: str
    is_uncertain: bool
    uncertainty_note: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    people: list[MemoryPersonRead]


class MemoryList(BaseModel):
    items: list[MemoryRead]
    next_cursor: str | None
    total: int
