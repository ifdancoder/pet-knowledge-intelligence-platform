from sqlalchemy.ext.asyncio import AsyncSession

from domain.ingestion.entities import Source
from infrastructure.ingestion.async_repository import SqlAlchemyAsyncSourceRepository


async def test_async_source_repository_add_and_get(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAsyncSourceRepository(db_session)
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/a.pdf")
    await repo.add(source)

    fetched = await repo.get_by_id(source.id)
    assert fetched == source
    assert await repo.get_by_id("missing") is None
