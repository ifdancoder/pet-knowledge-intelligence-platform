from typing import Any

from elasticsearch import Elasticsearch

from domain.ingestion.entities import Chunk


class ElasticsearchIndexer:
    def __init__(self, *, url: str, index_name: str = "chunks") -> None:
        self._client = Elasticsearch(url)
        self._index_name = index_name
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

    def index_chunks(self, chunks: list[Chunk]) -> None:
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
