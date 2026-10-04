from typing import Protocol

from domain.ingestion.entities import Chunk, Document, Source


class SourceRepository(Protocol):
    """Sync — used by Celery pipeline stage services."""

    def add(self, source: Source) -> None: ...
    def get_by_id(self, source_id: str) -> Source | None: ...
    def update(self, source: Source) -> None: ...


class DocumentRepository(Protocol):
    def add(self, document: Document) -> None: ...
    def get_by_source_id(self, source_id: str) -> Document | None: ...
    def update(self, document: Document) -> None: ...


class ChunkRepository(Protocol):
    def add_many(self, chunks: list[Chunk]) -> None: ...
    def list_by_source_id(self, source_id: str) -> list[Chunk]: ...
    def update_embeddings(self, chunks: list[Chunk]) -> None: ...


class SourceLoader(Protocol):
    """The one async port — bridged by a single asyncio.run() in ExtractDocumentService."""

    async def load(self, source: Source, file_bytes: bytes) -> str: ...


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SearchIndexer(Protocol):
    def index_chunks(self, chunks: list[Chunk], source_type: str) -> None: ...


class Storage(Protocol):
    """Sync. Celery calls it directly; the async API bridges via run_in_threadpool."""

    def upload(self, key: str, data: bytes) -> None: ...
    def download(self, key: str) -> bytes: ...


class AsyncSourceRepository(Protocol):
    """Async — used only by the API's upload/status endpoints."""

    async def add(self, source: Source) -> None: ...
    async def get_by_id(self, source_id: str) -> Source | None: ...


class AsyncChunkRepository(Protocol):
    """Async — used only by Search's read path, mirrors AsyncSourceRepository."""

    async def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]: ...
