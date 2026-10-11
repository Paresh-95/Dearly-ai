from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ConsentType


class ConsentCreate(BaseModel):
    consent_type: ConsentType
    granted: bool
    policy_version: str = Field(min_length=1, max_length=50)
    # None = account-level consent (e.g. data processing in general); set = scoped to one
    # family member profile (reserved for future per-profile consents such as voice synthesis).
    person_profile_id: UUID | None = None
    provider: str | None = Field(default=None, max_length=100)
    details: dict[str, Any] = Field(default_factory=dict)


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    consent_type: ConsentType
    granted: bool
    policy_version: str
    person_profile_id: UUID | None
    provider: str | None
    details: dict[str, Any]
    created_at: datetime


class ConsentList(BaseModel):
    items: list[ConsentRead]
