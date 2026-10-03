from collections.abc import Iterator

import pytest
from testcontainers.elasticsearch import ElasticSearchContainer

from domain.ingestion.entities import Chunk
from infrastructure.ingestion.search_index import ElasticsearchIndexer


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
    indexer.index_chunks(chunks)
    indexer.refresh()  # test-only: force the index to be searchable immediately

    results = indexer.search(query="fox", workspace_id="w1")

    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"
