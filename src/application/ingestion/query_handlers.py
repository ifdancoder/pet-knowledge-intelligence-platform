from application.ingestion.queries import GetSourceStatusQuery
from domain.ingestion.entities import Source
from domain.ingestion.ports import AsyncSourceRepository


class GetSourceStatusQueryHandler:
    def __init__(self, sources: AsyncSourceRepository) -> None:
        self._sources = sources

    async def handle(self, query: GetSourceStatusQuery) -> Source | None:
        return await self._sources.get_by_id(query.source_id)
