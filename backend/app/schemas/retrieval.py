from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.retrieval.pipeline import SearchMode


class RetrievalSearchRequest(BaseModel):
    person_profile_id: UUID
    query: str = Field(min_length=1, max_length=1000)
    mode: SearchMode = "hybrid"
    limit: int = Field(default=8, ge=1, le=50)
    category: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    people: list[str] | None = Field(default=None, max_length=20)


class RetrievalResultItem(BaseModel):
    memory_id: UUID
    chunk_id: UUID
    text: str
    score: float
    metadata: dict[str, Any]


class RetrievalDiagnostics(BaseModel):
    """Developer-facing only — never rendered to the person asking the question (brief §7:
    keep diagnostics separate from user-facing text)."""

    mode_used: SearchMode
    dense_count: int
    keyword_count: int
    fused_count: int
    took_ms: float
    dense_error: str | None = None


class RetrievalSearchResponse(BaseModel):
    items: list[RetrievalResultItem]
    diagnostics: RetrievalDiagnostics
