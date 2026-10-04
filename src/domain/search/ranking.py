from typing import Any


def reciprocal_rank_fusion(
    *, keyword_hits: list[dict[str, Any]], vector_hits: list[dict[str, Any]], k: int = 60
) -> list[tuple[str, float]]:
    """Returns [(chunk_id, fused_score), ...] sorted by fused_score descending.
    Each input list is assumed already ranked best-first; only rank position is used,
    not the hits' own scores — this is what makes RRF immune to incomparable score scales."""
    scores: dict[str, float] = {}
    for hits in (keyword_hits, vector_hits):
        for rank, hit in enumerate(hits, start=1):
            scores[hit["chunk_id"]] = scores.get(hit["chunk_id"], 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
