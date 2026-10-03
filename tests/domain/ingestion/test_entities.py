import pytest

from domain.ingestion.entities import Chunk, Document, Source
from domain.ingestion.exceptions import InvalidStatusTransitionError


def test_source_create_starts_queued() -> None:
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/abc.pdf")
    assert len(source.id) == 26
    assert source.status == "queued"
    assert source.error is None


def test_source_status_transitions_follow_the_pipeline() -> None:
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/abc.pdf")
    source.mark_extracting()
    assert source.status == "extracting"
    source.mark_normalizing()
    assert source.status == "normalizing"
    source.mark_chunking()
    assert source.status == "chunking"
    source.mark_embedding()
    assert source.status == "embedding"
    source.mark_indexing()
    assert source.status == "indexing"
    source.mark_indexed()
    assert source.status == "indexed"


def test_source_rejects_skipping_a_stage() -> None:
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/abc.pdf")
    with pytest.raises(InvalidStatusTransitionError):
        source.mark_chunking()


def test_source_mark_failed_records_error_from_any_status() -> None:
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/abc.pdf")
    source.mark_extracting()
    source.mark_failed("extraction blew up")
    assert source.status == "failed"
    assert source.error == "extraction blew up"


def test_source_rejects_transition_once_failed() -> None:
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/abc.pdf")
    source.mark_failed("boom")
    with pytest.raises(InvalidStatusTransitionError):
        source.mark_extracting()


def test_document_and_chunk_are_plain_dataclasses() -> None:
    document = Document(id="d1", source_id="s1", raw_text="hello world")
    assert document.raw_text == "hello world"
    chunk = Chunk(
        id="c1", source_id="s1", document_id="d1", workspace_id="w1", order_index=0, text="hello"
    )
    assert chunk.embedding is None
