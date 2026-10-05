import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from infrastructure.ingestion.models import ChunkModel, DocumentModel, SourceModel

pytestmark = pytest.mark.integration

def test_source_model_round_trip(sync_db_session: Session) -> None:
    source = SourceModel(
        id="s1", workspace_id="w1", type="pdf", storage_key="w1/x.pdf", status="queued"
    )
    sync_db_session.add(source)
    sync_db_session.flush()

    fetched = sync_db_session.execute(select(SourceModel).where(SourceModel.id == "s1")).scalar_one()
    assert fetched.status == "queued"


def test_chunk_model_stores_a_1536_dim_vector(sync_db_session: Session) -> None:
    sync_db_session.add(SourceModel(id="s2", workspace_id="w1", type="pdf", storage_key="w1/y.pdf"))
    sync_db_session.flush()
    sync_db_session.add(DocumentModel(id="d1", source_id="s2", raw_text="hello"))
    sync_db_session.flush()

    embedding = [0.0] * 1536
    chunk = ChunkModel(
        id="c1",
        source_id="s2",
        document_id="d1",
        workspace_id="w1",
        order_index=0,
        text="hello",
        embedding=embedding,
    )
    sync_db_session.add(chunk)
    sync_db_session.flush()

    fetched = sync_db_session.execute(select(ChunkModel).where(ChunkModel.id == "c1")).scalar_one()
    assert len(fetched.embedding) == 1536
