from sentence_transformers import CrossEncoder

from domain.search.entities import SearchResult

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    def __init__(self, *, device: str = "cpu") -> None:
        # No GPU/fork-safety concern here (unlike LocalEmbeddingProvider): this model is
        # constructed inside the FastAPI process, which never forks per-request. CPU is
        # just the simplest, most portable default, not a correctness requirement.
        self._model = CrossEncoder(_MODEL_NAME, device=device)

    def rerank(self, *, query: str, results: list[SearchResult], limit: int) -> list[SearchResult]:
        if not results:
            return []
        pairs = [(query, r.text) for r in results]
        scores = self._model.predict(pairs)
        ranked = sorted(zip(results, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        return [SearchResult(r.chunk_id, r.source_id, r.text, float(score)) for r, score in ranked[:limit]]
