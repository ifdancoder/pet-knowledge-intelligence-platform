from sentence_transformers import SentenceTransformer

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_NATIVE_DIMENSION = 384
TARGET_DIMENSION = 1536


class LocalEmbeddingProvider:
    dimension = TARGET_DIMENSION

    def __init__(self, *, device: str = "cpu") -> None:
        # CUDA requires a non-prefork Celery pool, such as --pool=solo.
        self._model = SentenceTransformer(_MODEL_NAME, device=device)

    def embed(self, texts: list[str]) -> list[list[float]]:
        raw_vectors = self._model.encode(texts, convert_to_numpy=False)
        padding = [0.0] * (TARGET_DIMENSION - _NATIVE_DIMENSION)
        return [list(vector) + padding for vector in raw_vectors]
