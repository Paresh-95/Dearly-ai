"""The structured-output contract between the LLM memory-candidate extractor and the
ingestion worker. Not a public API schema — never returned directly from an endpoint."""

from pydantic import BaseModel, Field


class CandidatePerson(BaseModel):
    name: str
    relationship: str | None = None


class MemoryCandidate(BaseModel):
    title: str = Field(max_length=300)
    description: str = Field(max_length=20_000)
    people: list[CandidatePerson] = Field(default_factory=list)
    date_text: str | None = None
    location: str | None = None
    category: str | None = None
    quotations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    uncertainty_note: str | None = None
    # 1-indexed positions into the source's segments, so the caller can link each candidate
    # back to the exact passage(s) it was drawn from (-> memory_sources).
    supporting_segment_ordinals: list[int] = Field(default_factory=list)


class MemoryCandidateBatch(BaseModel):
    """Top-level shape for the LLM call — OpenAI's structured-output mode wants a JSON
    object, not a bare array, as the schema root."""

    candidates: list[MemoryCandidate] = Field(default_factory=list)
