from typing import Any

from elasticsearch import Elasticsearch

from domain.ingestion.entities import Chunk


class ElasticsearchIndexer:
    def __init__(self, *, url: str, index_name: str = "chunks") -> None:
        self._client = Elasticsearch(url)
        self._index_name = index_name
        self._index_ensured = False

    def _ensure_index(self) -> None:
        # Avoid network access while application modules are being imported.
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
                        "source_type": {"type": "keyword"},
                        "text": {"type": "text"},
                    }
                },
            )
        self._index_ensured = True

    def index_chunks(self, chunks: list[Chunk], source_type: str) -> None:
        self._ensure_index()
        for chunk in chunks:
            self._client.index(
                index=self._index_name,
                id=chunk.id,
                document={
                    "chunk_id": chunk.id,
                    "source_id": chunk.source_id,
                    "workspace_id": chunk.workspace_id,
                    "source_type": source_type,
                    "text": chunk.text,
                },
            )

    def refresh(self) -> None:
        self._client.indices.refresh(index=self._index_name)

    def search(
        self, *, query: str, workspace_id: str, source_type: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        self._ensure_index()
        filters: list[dict[str, Any]] = [{"term": {"workspace_id": workspace_id}}]
        if source_type is not None:
            filters.append({"term": {"source_type": source_type}})
        response = self._client.search(
            index=self._index_name,
            size=limit,
            query={"bool": {"must": {"match": {"text": query}}, "filter": filters}},
        )
        return [{**hit["_source"], "score": hit["_score"]} for hit in response["hits"]["hits"]]
