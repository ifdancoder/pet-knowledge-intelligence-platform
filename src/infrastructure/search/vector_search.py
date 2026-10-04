from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.ingestion.models import ChunkModel, SourceModel


class PgVectorSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self, *, query_embedding: list[float], workspace_id: str, source_type: str | None, limit: int
    ) -> list[dict[str, Any]]:
        stmt = (
            select(ChunkModel, ChunkModel.embedding.cosine_distance(query_embedding).label("distance"))
            .join(SourceModel, SourceModel.id == ChunkModel.source_id)
            .where(ChunkModel.workspace_id == workspace_id, ChunkModel.embedding.is_not(None))
            .order_by("distance")
            .limit(limit)
        )
        if source_type is not None:
            stmt = stmt.where(SourceModel.type == source_type)
        rows = await self._session.execute(stmt)
        return [{"chunk_id": chunk.id, "score": 1.0 - distance} for chunk, distance in rows.all()]
