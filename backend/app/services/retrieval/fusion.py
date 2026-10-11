"""Reciprocal Rank Fusion: combines ranked lists from independent retrieval methods using
only each result's *rank* within its own list, not its raw score — dense cosine similarity
and FTS ts_rank are not on comparable scales, so merging by rank avoids one method dominating
just because its score happens to be numerically larger."""

from uuid import UUID

from app.services.retrieval.base import RetrievedChunk


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievedChunk]], *, k: int = 60
) -> list[tuple[RetrievedChunk, float]]:
    scores: dict[UUID, float] = {}
    representative: dict[UUID, RetrievedChunk] = {}

    for results in result_lists:
        for rank, chunk in enumerate(results, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
            representative.setdefault(chunk.chunk_id, chunk)

    ranked_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [(representative[cid], scores[cid]) for cid in ranked_ids]
