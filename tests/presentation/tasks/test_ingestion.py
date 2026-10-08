import fakeredis
import pytest

import presentation.tasks.ingestion as ingestion_tasks
from domain.ingestion.entities import Chunk, Document, Source
from worker import app


class FakeSourceRepository:
    def __init__(self, sources: dict[str, Source]) -> None:
        self._sources = sources

    def add(self, source: Source) -> None:
        self._sources[source.id] = source

    def get_by_id(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def update(self, source: Source) -> None:
        self._sources[source.id] = source


class FakeDocumentRepository:
    def __init__(self, documents: dict[str, Document]) -> None:
        self._documents = documents

    def add(self, document: Document) -> None:
        self._documents[document.source_id] = document

    def get_by_source_id(self, source_id: str) -> Document | None:
        return self._documents.get(source_id)

    def update(self, document: Document) -> None:
        self._documents[document.source_id] = document


class FakeChunkRepository:
    def __init__(self, chunks: dict[str, list[Chunk]]) -> None:
        self._chunks = chunks

    def add_many(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self._chunks.setdefault(chunk.source_id, []).append(chunk)

    def list_by_source_id(self, source_id: str) -> list[Chunk]:
        return self._chunks.get(source_id, [])

    def update_embeddings(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            for existing in self._chunks.get(chunk.source_id, []):
                if existing.id == chunk.id:
                    existing.embedding = chunk.embedding


class FakeSessionLocal:
    """In-memory session factory used by repository fakes."""

    def __init__(self) -> None:
        self.sources: dict[str, Source] = {}
        self.documents: dict[str, Document] = {}
        self.chunks: dict[str, list[Chunk]] = {}

    def __call__(self) -> "FakeSessionLocal":
        return self

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass


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
        return [[1.0, 2.0, 3.0, 4.0] for _ in texts]


class FakeSearchIndexer:
    def __init__(self) -> None:
        self.indexed: list[Chunk] = []
        self.last_source_type: str | None = None

    def index_chunks(self, chunks: list[Chunk], source_type: str) -> None:
        self.indexed.extend(chunks)
        self.last_source_type = source_type


@pytest.fixture(autouse=True)
def _eager_mode() -> None:
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True


@pytest.fixture
def fake_session_local(monkeypatch: pytest.MonkeyPatch) -> FakeSessionLocal:
    fake = FakeSessionLocal()
    monkeypatch.setattr(ingestion_tasks, "_SessionLocal", fake)
    return fake


def test_full_chain_processes_a_source_to_indexed(
    monkeypatch: pytest.MonkeyPatch, fake_session_local: FakeSessionLocal
) -> None:
    monkeypatch.setattr(ingestion_tasks, "_redis_client", fakeredis.FakeRedis())
    monkeypatch.setattr(ingestion_tasks, "_loader_registry", FakeSourceLoaderRegistry())
    monkeypatch.setattr(ingestion_tasks, "_embedding_provider", FakeEmbeddingProvider())
    indexer = FakeSearchIndexer()
    monkeypatch.setattr(ingestion_tasks, "_search_indexer", indexer)

    files = {"w1/source.md": b"hello world, this is a test document"}
    monkeypatch.setattr(ingestion_tasks, "_storage", FakeStorage(files))

    def fake_source_repo_factory(session: FakeSessionLocal) -> FakeSourceRepository:
        return FakeSourceRepository(session.sources)

    def fake_document_repo_factory(session: FakeSessionLocal) -> FakeDocumentRepository:
        return FakeDocumentRepository(session.documents)

    def fake_chunk_repo_factory(session: FakeSessionLocal) -> FakeChunkRepository:
        return FakeChunkRepository(session.chunks)

    monkeypatch.setattr(ingestion_tasks, "SqlAlchemySourceRepository", fake_source_repo_factory)
    monkeypatch.setattr(ingestion_tasks, "SqlAlchemyDocumentRepository", fake_document_repo_factory)
    monkeypatch.setattr(ingestion_tasks, "SqlAlchemyChunkRepository", fake_chunk_repo_factory)

    source = Source.create(workspace_id="w1", type="markdown", storage_key="w1/source.md")
    fake_session_local.sources[source.id] = source

    ingestion_tasks.extract_document.delay(source.id)

    final_source = fake_session_local.sources[source.id]
    assert final_source.status == "indexed"
    assert len(fake_session_local.chunks[source.id]) >= 1
    assert all(c.embedding is not None for c in fake_session_local.chunks[source.id])
    assert len(indexer.indexed) >= 1
