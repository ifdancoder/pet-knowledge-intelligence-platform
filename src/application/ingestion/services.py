import asyncio
from typing import Protocol

from domain.ingestion.chunking import split_into_chunks
from domain.ingestion.entities import Chunk, Document
from domain.ingestion.ports import (
    ChunkRepository,
    DocumentRepository,
    EmbeddingProvider,
    SearchIndexer,
    SourceLoader,
    SourceRepository,
    Storage,
)
from shared.ids import generate_id


class SourceLoaderRegistryProtocol(Protocol):
    """Narrow structural shape ExtractDocumentService depends on, so the application
    layer does not need to import the concrete infrastructure registry class."""

    def get(self, source_type: str) -> SourceLoader: ...


class ExtractDocumentService:
    def __init__(
        self,
        sources: SourceRepository,
        documents: DocumentRepository,
        storage: Storage,
        loader_registry: SourceLoaderRegistryProtocol,
    ) -> None:
        self._sources = sources
        self._documents = documents
        self._storage = storage
        self._loader_registry = loader_registry

    def run(self, source_id: str) -> None:
        source = self._sources.get_by_id(source_id)
        assert source is not None
        if source.status != "queued":
            return

        file_bytes = self._storage.download(source.storage_key)
        loader = self._loader_registry.get(source.type)
        raw_text = asyncio.run(loader.load(source, file_bytes))

        self._documents.add(Document(id=generate_id(), source_id=source.id, raw_text=raw_text))
        source.mark_extracting()
        self._sources.update(source)


class NormalizeDocumentService:
    def __init__(self, sources: SourceRepository, documents: DocumentRepository) -> None:
        self._sources = sources
        self._documents = documents

    def run(self, source_id: str) -> None:
        source = self._sources.get_by_id(source_id)
        assert source is not None
        if source.status != "extracting":
            return

        document = self._documents.get_by_source_id(source_id)
        assert document is not None
        document.raw_text = " ".join(document.raw_text.split())
        self._documents.update(document)

        source.mark_normalizing()
        self._sources.update(source)


class SplitIntoChunksService:
    def __init__(
        self, sources: SourceRepository, documents: DocumentRepository, chunks: ChunkRepository
    ) -> None:
        self._sources = sources
        self._documents = documents
        self._chunks = chunks

    def run(self, source_id: str) -> None:
        source = self._sources.get_by_id(source_id)
        assert source is not None
        if source.status != "normalizing":
            return

        document = self._documents.get_by_source_id(source_id)
        assert document is not None
        texts = split_into_chunks(document.raw_text)
        chunk_entities = [
            Chunk(
                id=generate_id(),
                source_id=source.id,
                document_id=document.id,
                workspace_id=source.workspace_id,
                order_index=index,
                text=text,
            )
            for index, text in enumerate(texts)
        ]
        self._chunks.add_many(chunk_entities)

        source.mark_chunking()
        self._sources.update(source)


class GenerateEmbeddingsService:
    def __init__(
        self, sources: SourceRepository, chunks: ChunkRepository, embedding_provider: EmbeddingProvider
    ) -> None:
        self._sources = sources
        self._chunks = chunks
        self._embedding_provider = embedding_provider

    def run(self, source_id: str) -> None:
        source = self._sources.get_by_id(source_id)
        assert source is not None
        if source.status != "chunking":
            return

        chunk_list = self._chunks.list_by_source_id(source_id)
        vectors = self._embedding_provider.embed([c.text for c in chunk_list])
        for chunk, vector in zip(chunk_list, vectors, strict=True):
            chunk.embedding = vector
        self._chunks.update_embeddings(chunk_list)

        source.mark_embedding()
        self._sources.update(source)


class IndexChunksService:
    def __init__(
        self, sources: SourceRepository, chunks: ChunkRepository, search_indexer: SearchIndexer
    ) -> None:
        self._sources = sources
        self._chunks = chunks
        self._search_indexer = search_indexer

    def run(self, source_id: str) -> None:
        source = self._sources.get_by_id(source_id)
        assert source is not None
        if source.status != "embedding":
            return

        chunk_list = self._chunks.list_by_source_id(source_id)
        self._search_indexer.index_chunks(chunk_list)

        source.mark_indexing()
        source.mark_indexed()
        self._sources.update(source)
