from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProfileBase(BaseModel):
    """Only `name` and `relationship` are required; emotionally difficult fields are optional."""

    name: str = Field(min_length=1, max_length=200)
    relationship: str = Field(min_length=1, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=200)
    languages: list[str] = Field(default_factory=list, max_length=20)
    biography: str | None = Field(default=None, max_length=20_000)
    personality: str | None = Field(default=None, max_length=20_000)
    favourite_expressions: list[str] = Field(default_factory=list, max_length=100)
    hobbies: list[str] = Field(default_factory=list, max_length=100)
    important_relationships: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    birth_date: date | None = None
    death_date: date | None = None


def _check_dates(birth: date | None, death: date | None) -> None:
    if birth and death and death < birth:
        raise ValueError("death_date cannot be before birth_date")


class ProfileCreate(ProfileBase):
    @model_validator(mode="after")
    def _dates(self) -> "ProfileCreate":
        _check_dates(self.birth_date, self.death_date)
        return self


class ProfileUpdate(BaseModel):
    """All fields optional; only provided fields are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    relationship: str | None = Field(default=None, min_length=1, max_length=100)
    preferred_name: str | None = Field(default=None, max_length=200)
    languages: list[str] | None = Field(default=None, max_length=20)
    biography: str | None = Field(default=None, max_length=20_000)
    personality: str | None = Field(default=None, max_length=20_000)
    favourite_expressions: list[str] | None = Field(default=None, max_length=100)
    hobbies: list[str] | None = Field(default=None, max_length=100)
    important_relationships: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    death_date: date | None = None

    @model_validator(mode="after")
    def _dates(self) -> "ProfileUpdate":
        _check_dates(self.birth_date, self.death_date)
        return self


class ProfileRead(ProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ProfileList(BaseModel):
    items: list[ProfileRead]
