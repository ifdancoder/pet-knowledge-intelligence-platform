from sqlalchemy.orm import Session

from domain.ingestion.entities import Chunk, Document, Source
from infrastructure.ingestion.repository import (
    SqlAlchemyChunkRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemySourceRepository,
)


def test_source_repository_add_get_update(sync_db_session: Session) -> None:
    repo = SqlAlchemySourceRepository(sync_db_session)
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/a.pdf")
    repo.add(source)

    fetched = repo.get_by_id(source.id)
    assert fetched == source

    source.mark_extracting()
    repo.update(source)
    refetched = repo.get_by_id(source.id)
    assert refetched is not None
    assert refetched.status == "extracting"

    assert repo.get_by_id("missing") is None


def test_document_repository_add_and_get(sync_db_session: Session) -> None:
    sources = SqlAlchemySourceRepository(sync_db_session)
    source = Source.create(workspace_id="w1", type="markdown", storage_key="w1/b.md")
    sources.add(source)

    documents = SqlAlchemyDocumentRepository(sync_db_session)
    document = Document(id="d1", source_id=source.id, raw_text="hello world")
    documents.add(document)

    fetched = documents.get_by_source_id(source.id)
    assert fetched == document
    assert documents.get_by_source_id("missing") is None

    document.raw_text = "normalized text"
    documents.update(document)
    refetched = documents.get_by_source_id(source.id)
    assert refetched is not None
    assert refetched.raw_text == "normalized text"


def test_chunk_repository_add_many_list_and_update_embeddings(sync_db_session: Session) -> None:
    sources = SqlAlchemySourceRepository(sync_db_session)
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/c.pdf")
    sources.add(source)

    documents = SqlAlchemyDocumentRepository(sync_db_session)
    document = Document(id="d2", source_id=source.id, raw_text="hello world")
    documents.add(document)

    chunks = SqlAlchemyChunkRepository(sync_db_session)
    chunk_list = [
        Chunk(id="c1", source_id=source.id, document_id="d2", workspace_id="w1", order_index=0, text="a"),
        Chunk(id="c2", source_id=source.id, document_id="d2", workspace_id="w1", order_index=1, text="b"),
    ]
    chunks.add_many(chunk_list)

    fetched = chunks.list_by_source_id(source.id)
    assert len(fetched) == 2
    assert all(c.embedding is None for c in fetched)

    chunk_list[0].embedding = [0.1] * 1536
    chunk_list[1].embedding = [0.2] * 1536
    chunks.update_embeddings(chunk_list)

    refetched = chunks.list_by_source_id(source.id)
    assert all(c.embedding is not None and len(c.embedding) == 1536 for c in refetched)
