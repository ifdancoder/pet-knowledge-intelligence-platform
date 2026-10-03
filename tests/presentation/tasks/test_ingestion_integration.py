from collections.abc import Iterator

import pytest
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.elasticsearch import ElasticSearchContainer
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

import presentation.tasks.ingestion as ingestion_tasks
from domain.ingestion.entities import Source
from infrastructure.database.base import Base
from infrastructure.ingestion.embeddings.local_provider import LocalEmbeddingProvider
from infrastructure.ingestion.repository import (
    SqlAlchemyChunkRepository,
    SqlAlchemySourceRepository,
)
from infrastructure.ingestion.search_index import ElasticsearchIndexer
from infrastructure.ingestion.source_loaders.registry import SourceLoaderRegistry
from infrastructure.ingestion.storage import S3Storage
from worker import app


@pytest.fixture(scope="module")
def pg_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(image="pgvector/pgvector:pg16", driver="psycopg2") as container:
        yield container


@pytest.fixture(scope="module")
def minio_container() -> Iterator[MinioContainer]:
    with MinioContainer(image="minio/minio:latest") as container:
        yield container


@pytest.fixture(scope="module")
def es_container() -> Iterator[ElasticSearchContainer]:
    with ElasticSearchContainer("docker.elastic.co/elasticsearch/elasticsearch:8.15.0") as container:
        yield container


@pytest.fixture(scope="module")
def redis_container() -> Iterator[RedisContainer]:
    with RedisContainer() as container:
        yield container


@pytest.fixture(autouse=True)
def _eager_mode() -> None:
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True


def test_full_chain_against_real_infrastructure(
    monkeypatch: pytest.MonkeyPatch,
    pg_container: PostgresContainer,
    minio_container: MinioContainer,
    es_container: ElasticSearchContainer,
    redis_container: RedisContainer,
) -> None:
    sync_url = pg_container.get_connection_url()
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    monkeypatch.setattr(ingestion_tasks, "_SessionLocal", session_local)

    minio_config = minio_container.get_config()
    minio_client = minio_container.get_client()
    minio_client.make_bucket("sources")
    storage = S3Storage(
        endpoint_url=f"http://{minio_config['endpoint']}",
        access_key=minio_config["access_key"],
        secret_key=minio_config["secret_key"],
        bucket="sources",
    )
    monkeypatch.setattr(ingestion_tasks, "_storage", storage)

    es_host = es_container.get_container_host_ip()
    es_port = es_container.get_exposed_port(9200)
    indexer = ElasticsearchIndexer(url=f"http://{es_host}:{es_port}", index_name="integration-test-chunks")
    monkeypatch.setattr(ingestion_tasks, "_search_indexer", indexer)

    redis_client = redis.Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
    )
    monkeypatch.setattr(ingestion_tasks, "_redis_client", redis_client)

    monkeypatch.setattr(ingestion_tasks, "_loader_registry", SourceLoaderRegistry())
    monkeypatch.setattr(ingestion_tasks, "_embedding_provider", LocalEmbeddingProvider())

    source = Source.create(workspace_id="w1", type="markdown", storage_key="")
    source.storage_key = f"w1/{source.id}-notes.md"
    storage.upload(
        source.storage_key, b"# Real Infra Test\n\nThis document proves the pipeline works end to end."
    )

    session = session_local()
    try:
        SqlAlchemySourceRepository(session).add(source)
        session.commit()
    finally:
        session.close()

    ingestion_tasks.extract_document.delay(source.id)

    verify_session = session_local()
    try:
        final_source = SqlAlchemySourceRepository(verify_session).get_by_id(source.id)
        assert final_source is not None
        assert final_source.status == "indexed"

        stored_chunks = SqlAlchemyChunkRepository(verify_session).list_by_source_id(source.id)
        assert len(stored_chunks) >= 1
        assert all(c.embedding is not None and len(c.embedding) == 1536 for c in stored_chunks)
    finally:
        verify_session.close()

    indexer.refresh()
    results = indexer.search(query="pipeline", workspace_id="w1")
    assert len(results) >= 1

    engine.dispose()
