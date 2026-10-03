from infrastructure.ingestion.embeddings.local_provider import LocalEmbeddingProvider


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
