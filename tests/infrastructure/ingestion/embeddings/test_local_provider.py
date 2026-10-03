from unittest.mock import patch

from infrastructure.ingestion.embeddings.local_provider import LocalEmbeddingProvider


def test_local_provider_defaults_to_cpu() -> None:
    with patch("infrastructure.ingestion.embeddings.local_provider.SentenceTransformer") as mock_cls:
        LocalEmbeddingProvider()
        mock_cls.assert_called_once_with(
            "sentence-transformers/all-MiniLM-L6-v2", device="cpu"
        )


def test_local_provider_forwards_an_explicit_device() -> None:
    with patch("infrastructure.ingestion.embeddings.local_provider.SentenceTransformer") as mock_cls:
        LocalEmbeddingProvider(device="cuda")
        mock_cls.assert_called_once_with(
            "sentence-transformers/all-MiniLM-L6-v2", device="cuda"
        )


def test_local_provider_pads_to_1536_dims() -> None:
    provider = LocalEmbeddingProvider()
    assert provider.dimension == 1536

    vectors = provider.embed(["hello world", "another sentence"])

    assert len(vectors) == 2
    for vector in vectors:
        assert len(vector) == 1536


def test_local_provider_produces_consistent_embeddings_for_the_same_text() -> None:
    provider = LocalEmbeddingProvider()
    first = provider.embed(["same text"])[0]
    second = provider.embed(["same text"])[0]
    assert first == second
