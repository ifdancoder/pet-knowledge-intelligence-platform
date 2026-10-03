from sentence_transformers import SentenceTransformer

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_NATIVE_DIMENSION = 384
TARGET_DIMENSION = 1536


class LocalEmbeddingProvider:
    dimension = TARGET_DIMENSION

    def __init__(self) -> None:
        # Pinned to CPU: this model is loaded once at module-import time, before Celery's
        # prefork pool forks its worker processes. A GPU-selected model re-initializes CUDA
        # inside each fork on first use, which torch forbids ("Cannot re-initialize CUDA in
        # forked subprocess"). MiniLM is small enough that CPU inference is not a bottleneck.
        self._model = SentenceTransformer(_MODEL_NAME, device="cpu")

    def embed(self, texts: list[str]) -> list[list[float]]:
        raw_vectors = self._model.encode(texts, convert_to_numpy=False)
        padding = [0.0] * (TARGET_DIMENSION - _NATIVE_DIMENSION)
        return [list(vector) + padding for vector in raw_vectors]
