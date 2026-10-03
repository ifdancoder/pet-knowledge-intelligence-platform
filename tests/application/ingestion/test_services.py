from application.ingestion.services import (
    ExtractDocumentService,
    GenerateEmbeddingsService,
    IndexChunksService,
    NormalizeDocumentService,
    SplitIntoChunksService,
)
from domain.ingestion.entities import Chunk, Document, Source


class FakeSourceRepository:
    def __init__(self) -> None:
        self.sources_by_id: dict[str, Source] = {}

    def add(self, source: Source) -> None:
        self.sources_by_id[source.id] = source

    def get_by_id(self, source_id: str) -> Source | None:
        return self.sources_by_id.get(source_id)

    def update(self, source: Source) -> None:
        self.sources_by_id[source.id] = source


class FakeDocumentRepository:
    def __init__(self) -> None:
        self.documents_by_source_id: dict[str, Document] = {}

    def add(self, document: Document) -> None:
        self.documents_by_source_id[document.source_id] = document

    def get_by_source_id(self, source_id: str) -> Document | None:
        return self.documents_by_source_id.get(source_id)

    def update(self, document: Document) -> None:
        self.documents_by_source_id[document.source_id] = document


class FakeChunkRepository:
    def __init__(self) -> None:
        self.chunks_by_source_id: dict[str, list[Chunk]] = {}

    def add_many(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self.chunks_by_source_id.setdefault(chunk.source_id, []).append(chunk)

    def list_by_source_id(self, source_id: str) -> list[Chunk]:
        return self.chunks_by_source_id.get(source_id, [])

    def update_embeddings(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            existing = [c for c in self.chunks_by_source_id.get(chunk.source_id, []) if c.id == chunk.id]
            for c in existing:
                c.embedding = chunk.embedding


class FakeStorage:
    def __init__(self, files: dict[str, bytes]) -> None:
        self._files = files

    def upload(self, key: str, data: bytes) -> None:
        self._files[key] = data

    def download(self, key: str) -> bytes:
        return self._files[key]


class FakeSourceLoader:
    async def load(self, source: Source, file_bytes: bytes) -> str:
        return file_bytes.decode("utf-8")


class FakeSourceLoaderRegistry:
    def get(self, source_type: str) -> FakeSourceLoader:
        return FakeSourceLoader()


class FakeEmbeddingProvider:
    dimension = 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] * 4 for t in texts]


class FakeSearchIndexer:
    def __init__(self) -> None:
        self.indexed: list[Chunk] = []

    def index_chunks(self, chunks: list[Chunk]) -> None:
        self.indexed.extend(chunks)


def test_extract_document_service_creates_a_document_and_advances_status() -> None:
    sources = FakeSourceRepository()
    documents = FakeDocumentRepository()
    source = Source.create(workspace_id="w1", type="markdown", storage_key="w1/a.md")
    sources.add(source)
    storage = FakeStorage({"w1/a.md": b"hello world"})

    service = ExtractDocumentService(sources, documents, storage, FakeSourceLoaderRegistry())
    service.run(source.id)

    assert sources.get_by_id(source.id).status == "extracting"
    document = documents.get_by_source_id(source.id)
    assert document is not None
    assert document.raw_text == "hello world"


def test_extract_document_service_is_idempotent() -> None:
    sources = FakeSourceRepository()
    documents = FakeDocumentRepository()
    source = Source.create(workspace_id="w1", type="markdown", storage_key="w1/a.md")
    source.mark_extracting()
    source.mark_normalizing()
    sources.add(source)
    storage = FakeStorage({"w1/a.md": b"hello world"})

    service = ExtractDocumentService(sources, documents, storage, FakeSourceLoaderRegistry())
    service.run(source.id)  # already past "extracting" -> no-op

    assert documents.get_by_source_id(source.id) is None


def test_normalize_document_service_advances_status() -> None:
    sources = FakeSourceRepository()
    documents = FakeDocumentRepository()
    source = Source.create(workspace_id="w1", type="markdown", storage_key="w1/a.md")
    source.mark_extracting()
    sources.add(source)
    documents.add(Document(id="d1", source_id=source.id, raw_text="  hello   world  "))

    service = NormalizeDocumentService(sources, documents)
    service.run(source.id)

    assert sources.get_by_id(source.id).status == "normalizing"
    assert documents.get_by_source_id(source.id).raw_text == "hello world"


def test_split_into_chunks_service_persists_chunks_and_advances_status() -> None:
    sources = FakeSourceRepository()
    documents = FakeDocumentRepository()
    chunks = FakeChunkRepository()
    source = Source.create(workspace_id="w1", type="markdown", storage_key="w1/a.md")
    source.mark_extracting()
    source.mark_normalizing()
    sources.add(source)
    documents.add(Document(id="d1", source_id=source.id, raw_text="hello world"))

    service = SplitIntoChunksService(sources, documents, chunks)
    service.run(source.id)

    assert sources.get_by_id(source.id).status == "chunking"
    stored = chunks.list_by_source_id(source.id)
    assert len(stored) == 1
    assert stored[0].text == "hello world"
    assert stored[0].workspace_id == "w1"


def test_generate_embeddings_service_fills_in_embeddings_and_advances_status() -> None:
    sources = FakeSourceRepository()
    chunks = FakeChunkRepository()
    source = Source.create(workspace_id="w1", type="markdown", storage_key="w1/a.md")
    source.mark_extracting()
    source.mark_normalizing()
    source.mark_chunking()
    sources.add(source)
    chunks.add_many(
        [Chunk(id="c1", source_id=source.id, document_id="d1", workspace_id="w1", order_index=0, text="hi")]
    )

    service = GenerateEmbeddingsService(sources, chunks, FakeEmbeddingProvider())
    service.run(source.id)

    assert sources.get_by_id(source.id).status == "embedding"
    stored = chunks.list_by_source_id(source.id)
    assert stored[0].embedding == [2.0] * 4


def test_index_chunks_service_indexes_and_advances_status() -> None:
    sources = FakeSourceRepository()
    chunks = FakeChunkRepository()
    source = Source.create(workspace_id="w1", type="markdown", storage_key="w1/a.md")
    source.mark_extracting()
    source.mark_normalizing()
    source.mark_chunking()
    source.mark_embedding()
    sources.add(source)
    chunks.add_many(
        [
            Chunk(
                id="c1", source_id=source.id, document_id="d1", workspace_id="w1",
                order_index=0, text="hi", embedding=[1.0] * 4,
            )
        ]
    )

    indexer = FakeSearchIndexer()
    service = IndexChunksService(sources, chunks, indexer)
    service.run(source.id)

    assert sources.get_by_id(source.id).status == "indexed"
    assert len(indexer.indexed) == 1
    assert indexer.indexed[0].id == "c1"
