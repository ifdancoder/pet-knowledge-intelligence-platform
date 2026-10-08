import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.ingestion.entities import Source
from infrastructure.ingestion.async_repository import (
    SqlAlchemyAsyncChunkRepository,
    SqlAlchemyAsyncSourceRepository,
)
from infrastructure.ingestion.models import ChunkModel, DocumentModel, SourceModel

pytestmark = pytest.mark.integration

async def test_async_source_repository_add_and_get(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAsyncSourceRepository(db_session)
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/a.pdf")
    await repo.add(source)

    fetched = await repo.get_by_id(source.id)
    assert fetched == source
    assert await repo.get_by_id("missing") is None


async def test_list_by_workspace_id_returns_only_that_workspaces_sources(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAsyncSourceRepository(db_session)
    await repo.add(Source.create(workspace_id="w1", type="pdf", storage_key="w1/a.pdf"))
    await repo.add(Source.create(workspace_id="w2", type="pdf", storage_key="w2/b.pdf"))

    result = await repo.list_by_workspace_id("w1")

    assert len(result) == 1
    assert result[0].workspace_id == "w1"


async def test_async_chunk_repository_get_by_ids(db_session: AsyncSession) -> None:
    db_session.add(SourceModel(id="s1", workspace_id="w1", type="markdown", storage_key="w1/a.md"))
    await db_session.flush()
    db_session.add(DocumentModel(id="d1", source_id="s1", raw_text="hello world"))
    await db_session.flush()
    db_session.add_all(
        [
            ChunkModel(
                id="c1", source_id="s1", document_id="d1", workspace_id="w1",
                order_index=0, text="hello", embedding=[0.1] * 1536,
            ),
            ChunkModel(
                id="c2", source_id="s1", document_id="d1", workspace_id="w1",
                order_index=1, text="world", embedding=[0.2] * 1536,
            ),
        ]
    )
    await db_session.flush()

    repo = SqlAlchemyAsyncChunkRepository(db_session)
    chunks = await repo.get_by_ids(["c1", "missing-id"])

    assert len(chunks) == 1
    assert chunks[0].id == "c1"
    assert chunks[0].text == "hello"
