"""Shared result type passed between the dense/keyword searchers, the fusion step, and the
reranker. `score` means whatever the stage that produced it uses internally (cosine
similarity, ts_rank, RRF score, lexical-overlap fraction) — never compared across stages."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    memory_id: UUID
    text: str
    metadata: dict[str, Any]
    score: float
