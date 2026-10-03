from application.ingestion.command_handlers import UploadSourceCommandHandler
from application.ingestion.commands import UploadSourceCommand
from application.ingestion.queries import GetSourceStatusQuery
from application.ingestion.query_handlers import GetSourceStatusQueryHandler
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


async def test_get_source_status_returns_the_source() -> None:
    sources = FakeAsyncSourceRepository()
    storage = FakeStorage()
    upload_handler = UploadSourceCommandHandler(sources, storage)
    query_handler = GetSourceStatusQueryHandler(sources)

    source_id = await upload_handler.handle(
        UploadSourceCommand(workspace_id="w1", type="markdown", filename="notes.md", file_bytes=b"hello")
    )
    fetched = await query_handler.handle(GetSourceStatusQuery(source_id))

    assert fetched is not None
    assert fetched.id == source_id
    assert await query_handler.handle(GetSourceStatusQuery("missing")) is None
