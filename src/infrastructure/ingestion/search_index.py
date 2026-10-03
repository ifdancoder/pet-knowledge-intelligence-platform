from typing import Any

from elasticsearch import Elasticsearch

from domain.ingestion.entities import Chunk


class ElasticsearchIndexer:
    def __init__(self, *, url: str, index_name: str = "chunks") -> None:
        self._client = Elasticsearch(url)
        self._index_name = index_name
        self._index_ensured = False

    def _ensure_index(self) -> None:
        # Deferred to first real use, not the constructor: this adapter is built as a
        # module-level singleton at import time (presentation/tasks/ingestion.py), and a
        # network call in __init__ would make importing that module fail whenever
        # Elasticsearch isn't reachable yet, even for code paths that never touch search.
        if self._index_ensured:
            return
        if not self._client.indices.exists(index=self._index_name):
            self._client.indices.create(
                index=self._index_name,
                mappings={
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "source_id": {"type": "keyword"},
                        "workspace_id": {"type": "keyword"},
                        "text": {"type": "text"},
                    }
                },
            )
        self._index_ensured = True

    def index_chunks(self, chunks: list[Chunk]) -> None:
        self._ensure_index()
        for chunk in chunks:
            self._client.index(
                index=self._index_name,
                id=chunk.id,
                document={
                    "chunk_id": chunk.id,
                    "source_id": chunk.source_id,
                    "workspace_id": chunk.workspace_id,
                    "text": chunk.text,
                },
            )

    def refresh(self) -> None:
        self._client.indices.refresh(index=self._index_name)

    def search(self, *, query: str, workspace_id: str) -> list[dict[str, Any]]:
        self._ensure_index()
        response = self._client.search(
            index=self._index_name,
            query={
                "bool": {
                    "must": {"match": {"text": query}},
                    "filter": {"term": {"workspace_id": workspace_id}},
                }
            },
        )
        return [hit["_source"] for hit in response["hits"]["hits"]]
