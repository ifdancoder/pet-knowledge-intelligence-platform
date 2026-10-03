from application.ingestion.upload_service import SourceUploadService
from domain.ingestion.entities import Source


class FakeAsyncSourceRepository:
    def __init__(self) -> None:
        self.sources_by_id: dict[str, Source] = {}

    async def add(self, source: Source) -> None:
        self.sources_by_id[source.id] = source

    async def get_by_id(self, source_id: str) -> Source | None:
        return self.sources_by_id.get(source_id)


class FakeStorage:
    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}

    def upload(self, key: str, data: bytes) -> None:
        self.uploaded[key] = data

    def download(self, key: str) -> bytes:
        return self.uploaded[key]


async def test_upload_creates_a_queued_source_and_stores_the_file() -> None:
    sources = FakeAsyncSourceRepository()
    storage = FakeStorage()
    service = SourceUploadService(sources, storage)

    source = await service.upload(
        workspace_id="w1", type="markdown", filename="notes.md", file_bytes=b"hello"
    )

    assert source.status == "queued"
    assert source.workspace_id == "w1"
    stored = await sources.get_by_id(source.id)
    assert stored == source
    assert storage.uploaded[source.storage_key] == b"hello"


async def test_get_status_returns_the_source() -> None:
    sources = FakeAsyncSourceRepository()
    storage = FakeStorage()
    service = SourceUploadService(sources, storage)
    source = await service.upload(
        workspace_id="w1", type="markdown", filename="notes.md", file_bytes=b"hello"
    )

    fetched = await service.get_status(source.id)

    assert fetched == source
    assert await service.get_status("missing") is None
