import os
from typing import Any

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from application.ingestion.services import (
    ExtractDocumentService,
    GenerateEmbeddingsService,
    IndexChunksService,
    NormalizeDocumentService,
    SplitIntoChunksService,
)
from infrastructure.ingestion.embeddings.local_provider import LocalEmbeddingProvider
from infrastructure.ingestion.embeddings.openai_provider import OpenAIEmbeddingProvider
from infrastructure.ingestion.locking import source_lock
from infrastructure.ingestion.repository import (
    SqlAlchemyChunkRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemySourceRepository,
)
from infrastructure.ingestion.search_index import ElasticsearchIndexer
from infrastructure.ingestion.source_loaders.registry import SourceLoaderRegistry
from infrastructure.ingestion.storage import S3Storage
from worker import app

_sync_database_url = os.environ.get(
    "SYNC_DATABASE_URL", "postgresql+psycopg2://kip:kip@localhost:5434/kip"
)
_engine = create_engine(_sync_database_url)
_SessionLocal = sessionmaker(bind=_engine)

_storage = S3Storage(
    endpoint_url=os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000"),
    access_key=os.environ.get("S3_ACCESS_KEY", "kip"),
    secret_key=os.environ.get("S3_SECRET_KEY", "kipkipkip"),
    bucket=os.environ.get("S3_BUCKET", "sources"),
)
_search_indexer = ElasticsearchIndexer(url=os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
_redis_client = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6380/0"))
_loader_registry = SourceLoaderRegistry()
_embedding_provider = (
    OpenAIEmbeddingProvider()
    if os.environ.get("EMBEDDING_PROVIDER", "local") == "openai"
    else LocalEmbeddingProvider(device=os.environ.get("EMBEDDING_DEVICE", "cpu"))
)

_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 600,
    "max_retries": 5,
}


@app.task(bind=True, **_RETRY_KWARGS)
def extract_document(self: Any, source_id: str) -> None:
    with source_lock(_redis_client, source_id):
        session = _SessionLocal()
        try:
            service = ExtractDocumentService(
                SqlAlchemySourceRepository(session),
                SqlAlchemyDocumentRepository(session),
                _storage,
                _loader_registry,
            )
            service.run(source_id)
            session.commit()
        finally:
            session.close()
    normalize_document.delay(source_id)


@app.task(bind=True, **_RETRY_KWARGS)
def normalize_document(self: Any, source_id: str) -> None:
    with source_lock(_redis_client, source_id):
        session = _SessionLocal()
        try:
            service = NormalizeDocumentService(
                SqlAlchemySourceRepository(session), SqlAlchemyDocumentRepository(session)
            )
            service.run(source_id)
            session.commit()
        finally:
            session.close()
    split_into_chunks_task.delay(source_id)


@app.task(bind=True, **_RETRY_KWARGS)
def split_into_chunks_task(self: Any, source_id: str) -> None:
    with source_lock(_redis_client, source_id):
        session = _SessionLocal()
        try:
            service = SplitIntoChunksService(
                SqlAlchemySourceRepository(session),
                SqlAlchemyDocumentRepository(session),
                SqlAlchemyChunkRepository(session),
            )
            service.run(source_id)
            session.commit()
        finally:
            session.close()
    generate_embeddings.delay(source_id)


@app.task(bind=True, **_RETRY_KWARGS)
def generate_embeddings(self: Any, source_id: str) -> None:
    with source_lock(_redis_client, source_id):
        session = _SessionLocal()
        try:
            service = GenerateEmbeddingsService(
                SqlAlchemySourceRepository(session), SqlAlchemyChunkRepository(session), _embedding_provider
            )
            service.run(source_id)
            session.commit()
        finally:
            session.close()
    index_chunks.delay(source_id)


@app.task(bind=True, **_RETRY_KWARGS)
def index_chunks(self: Any, source_id: str) -> None:
    with source_lock(_redis_client, source_id):
        session = _SessionLocal()
        try:
            service = IndexChunksService(
                SqlAlchemySourceRepository(session), SqlAlchemyChunkRepository(session), _search_indexer
            )
            service.run(source_id)
            session.commit()
        finally:
            session.close()
