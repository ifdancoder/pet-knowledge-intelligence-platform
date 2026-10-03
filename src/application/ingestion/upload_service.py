from starlette.concurrency import run_in_threadpool

from domain.ingestion.entities import Source
from domain.ingestion.ports import AsyncSourceRepository, Storage


class SourceUploadService:
    def __init__(self, sources: AsyncSourceRepository, storage: Storage) -> None:
        self._sources = sources
        self._storage = storage

    async def upload(self, *, workspace_id: str, type: str, filename: str, file_bytes: bytes) -> Source:
        source = Source.create(workspace_id=workspace_id, type=type, storage_key="")
        source.storage_key = f"{workspace_id}/{source.id}-{filename}"
        await self._sources.add(source)
        await run_in_threadpool(self._storage.upload, source.storage_key, file_bytes)
        return source

    async def get_status(self, source_id: str) -> Source | None:
        return await self._sources.get_by_id(source_id)
