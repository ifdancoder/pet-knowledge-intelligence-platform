import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.ingestion.models import ChunkModel, DocumentModel, SourceModel
from infrastructure.search.vector_search import PgVectorSearchRepository

pytestmark = pytest.mark.integration

async def _seed(db_session: AsyncSession, source_id: str, source_type: str, chunk_id: str, embedding: list[float]) -> None:
    # Flushed separately — SQLAlchemy's automatic FK-dependency insert ordering does not
    # reliably apply across mixed-mapper add_all() batches with the asyncpg driver.
    db_session.add(SourceModel(id=source_id, workspace_id="w1", type=source_type, storage_key=f"w1/{source_id}"))
    await db_session.flush()
    db_session.add(DocumentModel(id=f"doc-{source_id}", source_id=source_id, raw_text="irrelevant"))
    await db_session.flush()
    db_session.add(
        ChunkModel(
            id=chunk_id, source_id=source_id, document_id=f"doc-{source_id}", workspace_id="w1",
            order_index=0, text="irrelevant", embedding=embedding,
        )
    )
    await db_session.flush()


async def test_search_orders_by_cosine_similarity(db_session: AsyncSession) -> None:
    close_vector = [1.0] * 1536
    far_vector = [-1.0] * 1536
    await _seed(db_session, "s1", "markdown", "c-close", close_vector)
    await _seed(db_session, "s2", "markdown", "c-far", far_vector)

    repo = PgVectorSearchRepository(db_session)
    results = await repo.search(query_embedding=[1.0] * 1536, workspace_id="w1", source_type=None, limit=10)

    assert [r["chunk_id"] for r in results] == ["c-close", "c-far"]


async def test_search_filters_by_source_type(db_session: AsyncSession) -> None:
    await _seed(db_session, "s3", "pdf", "c-pdf", [1.0] * 1536)
    await _seed(db_session, "s4", "markdown", "c-md", [1.0] * 1536)

    repo = PgVectorSearchRepository(db_session)
    results = await repo.search(query_embedding=[1.0] * 1536, workspace_id="w1", source_type="pdf", limit=10)

    assert [r["chunk_id"] for r in results] == ["c-pdf"]


async def test_search_respects_limit(db_session: AsyncSession) -> None:
    for i in range(5):
        await _seed(db_session, f"s5{i}", "markdown", f"c5{i}", [1.0] * 1536)

    repo = PgVectorSearchRepository(db_session)
    results = await repo.search(query_embedding=[1.0] * 1536, workspace_id="w1", source_type=None, limit=2)

    assert len(results) == 2
