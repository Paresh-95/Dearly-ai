"""The structured-output contract between the answer generator and the conversation
pipeline. Not a public API schema — never returned directly from an endpoint."""

from pydantic import BaseModel, Field


class GroundedAnswer(BaseModel):
    answer: str = Field(max_length=4000)
    # 1-indexed positions into the numbered evidence passages given in the prompt, resolved
    # back to real memory ids server-side — never the model's own idea of a UUID (see
    # app/services/providers/llm.py's MemoryCandidate for the same pattern in Milestone 3).
    cited_evidence_numbers: list[int] = Field(default_factory=list)
    has_sufficient_evidence: bool
    conflict_detected: bool = False
    conflict_note: str | None = Field(default=None, max_length=1000)
