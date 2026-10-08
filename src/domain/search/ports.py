from typing import Any, Protocol

from domain.search.entities import SearchResult


class KeywordSearchPort(Protocol):
    def search(
        self, *, query: str, workspace_id: str, source_type: str | None, limit: int
    ) -> list[dict[str, Any]]: ...


class VectorSearchPort(Protocol):
    async def search(
        self, *, query_embedding: list[float], workspace_id: str, source_type: str | None, limit: int
    ) -> list[dict[str, Any]]: ...


class Reranker(Protocol):
    def rerank(self, *, query: str, results: list[SearchResult], limit: int) -> list[SearchResult]: ...
