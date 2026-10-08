from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.ingestion.entities import Chunk, Source
from infrastructure.ingestion.models import ChunkModel, SourceModel


class SqlAlchemyAsyncSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, source: Source) -> None:
        model = SourceModel(
            id=source.id,
            workspace_id=source.workspace_id,
            type=source.type,
            storage_key=source.storage_key,
            status=source.status,
            error=source.error,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, source_id: str) -> Source | None:
        result = await self._session.execute(select(SourceModel).where(SourceModel.id == source_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return Source(
            id=model.id,
            workspace_id=model.workspace_id,
            type=model.type,
            storage_key=model.storage_key,
            status=model.status,
            error=model.error,
        )

    async def list_by_workspace_id(self, workspace_id: str) -> list[Source]:
        result = await self._session.execute(
            select(SourceModel).where(SourceModel.workspace_id == workspace_id).order_by(SourceModel.id)
        )
        return [
            Source(
                id=model.id,
                workspace_id=model.workspace_id,
                type=model.type,
                storage_key=model.storage_key,
                status=model.status,
                error=model.error,
            )
            for model in result.scalars().all()
        ]


class SqlAlchemyAsyncChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        result = await self._session.execute(select(ChunkModel).where(ChunkModel.id.in_(chunk_ids)))
        return [
            Chunk(
                id=m.id, source_id=m.source_id, document_id=m.document_id, workspace_id=m.workspace_id,
                order_index=m.order_index, text=m.text, embedding=m.embedding,
            )
            for m in result.scalars().all()
        ]
