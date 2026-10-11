"""Reranking interface. The default is deliberately not an ML model: the blueprint calls for
"a lightweight, transparent approach if an external reranking model is unavailable," tested
on real data before anything fancier is adopted (see evals/). `LexicalOverlapReranker` is
that transparent default — plain token overlap between the query and each candidate."""

import re
from abc import ABC, abstractmethod

from app.services.retrieval.base import RetrievedChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class Reranker(ABC):
    @abstractmethod
    def rerank(
        self, query: str, candidates: list[RetrievedChunk]
    ) -> list[tuple[RetrievedChunk, float]]: ...


class LexicalOverlapReranker(Reranker):
    """Score = fraction of the query's distinct tokens that also appear in the candidate's
    text. Ties (including an empty query) fall back to the candidate's incoming order."""

    def rerank(
        self, query: str, candidates: list[RetrievedChunk]
    ) -> list[tuple[RetrievedChunk, float]]:
        q_tokens = _tokenize(query)
        scored = [
            (c, len(q_tokens & _tokenize(c.text)) / len(q_tokens) if q_tokens else 0.0)
            for c in candidates
        ]
        # stable sort preserves incoming order among equal scores
        return sorted(scored, key=lambda pair: pair[1], reverse=True)
