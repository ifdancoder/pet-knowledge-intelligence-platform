import asyncio
from collections.abc import Iterator

import pytest
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.elasticsearch import ElasticSearchContainer
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

import presentation.tasks.ingestion as ingestion_tasks
from application.search.queries import SearchQuery
from application.search.query_handlers import HybridSearchQueryHandler, RerankingSearchQueryHandler
from domain.ingestion.entities import Source
from domain.search.entities import SearchResult
from infrastructure.database.base import Base
from infrastructure.ingestion.async_repository import SqlAlchemyAsyncChunkRepository
from infrastructure.ingestion.embeddings.local_provider import LocalEmbeddingProvider
from infrastructure.ingestion.repository import SqlAlchemySourceRepository
from infrastructure.ingestion.search_index import ElasticsearchIndexer
from infrastructure.ingestion.source_loaders.registry import SourceLoaderRegistry
from infrastructure.ingestion.storage import S3Storage
from infrastructure.search.reranker import CrossEncoderReranker
from infrastructure.search.vector_search import PgVectorSearchRepository
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


def test_search_finds_a_chunk_indexed_by_the_real_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    pg_container: PostgresContainer,
    minio_container: MinioContainer,
    es_container: ElasticSearchContainer,
    redis_container: RedisContainer,
) -> None:
    sync_url = pg_container.get_connection_url()
    sync_engine = create_engine(sync_url)
    with sync_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(sync_engine)
    session_local = sessionmaker(bind=sync_engine)
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
    indexer = ElasticsearchIndexer(url=f"http://{es_host}:{es_port}", index_name="search-integration-test")
    monkeypatch.setattr(ingestion_tasks, "_search_indexer", indexer)

    redis_client = redis.Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
    )
    monkeypatch.setattr(ingestion_tasks, "_redis_client", redis_client)

    monkeypatch.setattr(ingestion_tasks, "_loader_registry", SourceLoaderRegistry())
    local_provider = LocalEmbeddingProvider()
    monkeypatch.setattr(ingestion_tasks, "_embedding_provider", local_provider)

    source = Source.create(workspace_id="w1", type="markdown", storage_key="")
    source.storage_key = f"w1/{source.id}-notes.md"
    storage.upload(
        source.storage_key,
        b"# Search Integration Test\n\nThis document proves hybrid search works end to end.",
    )

    sync_session = session_local()
    try:
        SqlAlchemySourceRepository(sync_session).add(source)
        sync_session.commit()
    finally:
        sync_session.close()

    ingestion_tasks.extract_document.delay(source.id)
    indexer.refresh()

    async_url = sync_url.replace("+psycopg2", "+asyncpg")
    async_engine = create_async_engine(async_url)

    async def run_search() -> list[SearchResult]:
        async_session_local = async_sessionmaker(bind=async_engine, expire_on_commit=False)
        async with async_session_local() as session:
            inner = HybridSearchQueryHandler(
                indexer,
                PgVectorSearchRepository(session),
                local_provider,
                SqlAlchemyAsyncChunkRepository(session),
            )
            handler = RerankingSearchQueryHandler(inner, CrossEncoderReranker())
            return await handler.handle(
                SearchQuery(query="hybrid search", workspace_id="w1", source_type=None, limit=5)
            )

    # extract_document.delay(...) above bridges SourceLoader.load via asyncio.run() internally
    # (ExtractDocumentCommandHandler), so this test function must stay sync — asyncio.run()
    # cannot be called from within an already-running event loop. The search step is async
    # (AsyncSession-based), so it gets its own, separate asyncio.run() here instead.
    results = asyncio.run(run_search())
    asyncio.run(async_engine.dispose())

    assert len(results) >= 1
    assert any("hybrid search" in r.text for r in results)

    sync_engine.dispose()
