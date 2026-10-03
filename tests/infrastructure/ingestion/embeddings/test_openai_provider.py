from unittest.mock import MagicMock

from infrastructure.ingestion.embeddings.openai_provider import OpenAIEmbeddingProvider


def test_openai_provider_calls_the_embeddings_api_and_returns_vectors() -> None:
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.data = [MagicMock(embedding=[0.1] * 1536), MagicMock(embedding=[0.2] * 1536)]
    fake_client.embeddings.create.return_value = fake_response

    provider = OpenAIEmbeddingProvider(client=fake_client)
    vectors = provider.embed(["a", "b"])

    assert vectors == [[0.1] * 1536, [0.2] * 1536]
    fake_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small", input=["a", "b"]
    )
