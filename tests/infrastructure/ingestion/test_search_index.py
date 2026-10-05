from collections.abc import Iterator

import pytest
from testcontainers.elasticsearch import ElasticSearchContainer

from domain.ingestion.entities import Chunk
from infrastructure.ingestion.search_index import ElasticsearchIndexer

pytestmark = pytest.mark.integration

@pytest.fixture(scope="module")
def es_container() -> Iterator[ElasticSearchContainer]:
    with ElasticSearchContainer("docker.elastic.co/elasticsearch/elasticsearch:8.15.0") as container:
        yield container


@pytest.fixture
def indexer(es_container: ElasticSearchContainer) -> ElasticsearchIndexer:
    host = es_container.get_container_host_ip()
    port = es_container.get_exposed_port(9200)
    return ElasticsearchIndexer(url=f"http://{host}:{port}", index_name="test-chunks")


def test_index_chunks_makes_them_searchable(indexer: ElasticsearchIndexer) -> None:
    chunks = [
        Chunk(id="c1", source_id="s1", document_id="d1", workspace_id="w1", order_index=0, text="the quick brown fox"),
        Chunk(id="c2", source_id="s1", document_id="d1", workspace_id="w1", order_index=1, text="jumps over the lazy dog"),
    ]
    indexer.index_chunks(chunks, source_type="markdown")
    indexer.refresh()  # test-only: force the index to be searchable immediately

    results = indexer.search(query="fox", workspace_id="w1")

    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"
    assert "score" in results[0]


def test_search_filters_by_source_type(indexer: ElasticsearchIndexer) -> None:
    chunks = [Chunk(id="c3", source_id="s2", document_id="d2", workspace_id="w1", order_index=0, text="unique marker term")]
    indexer.index_chunks(chunks, source_type="pdf")
    indexer.refresh()

    assert len(indexer.search(query="marker", workspace_id="w1", source_type="pdf")) == 1
    assert len(indexer.search(query="marker", workspace_id="w1", source_type="markdown")) == 0


def test_search_respects_limit(indexer: ElasticsearchIndexer) -> None:
    chunks = [
        Chunk(id=f"c{i}", source_id="s3", document_id="d3", workspace_id="w1", order_index=i, text="limit test term")
        for i in range(5)
    ]
    indexer.index_chunks(chunks, source_type="markdown")
    indexer.refresh()

    assert len(indexer.search(query="limit", workspace_id="w1", limit=2)) == 2
