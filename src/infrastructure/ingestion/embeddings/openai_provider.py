import os

from openai import OpenAI


class OpenAIEmbeddingProvider:
    dimension = 1536

    def __init__(self, client: OpenAI | None = None) -> None:
        self._client = client or OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [item.embedding for item in response.data]
