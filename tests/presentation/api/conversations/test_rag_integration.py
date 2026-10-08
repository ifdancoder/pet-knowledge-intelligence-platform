from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.elasticsearch import ElasticSearchContainer
from testcontainers.postgres import PostgresContainer

from application.conversations.command_handlers import (
    CreateConversationCommandHandler,
    SendUserMessageCommandHandler,
)
from application.conversations.commands import CreateConversationCommand, SendUserMessageCommand
from application.conversations.services import GenerateAssistantReplyService
from application.search.query_handlers import HybridSearchQueryHandler, RerankingSearchQueryHandler
from domain.search.entities import SearchResult
from infrastructure.conversations.async_repository import (
    SqlAlchemyAsyncConversationRepository,
    SqlAlchemyAsyncMessageRepository,
)
from infrastructure.database.base import Base
from infrastructure.ingestion.async_repository import SqlAlchemyAsyncChunkRepository
from infrastructure.ingestion.embeddings.local_provider import LocalEmbeddingProvider
from infrastructure.ingestion.models import ChunkModel, DocumentModel, SourceModel
from infrastructure.ingestion.search_index import ElasticsearchIndexer
from infrastructure.search.vector_search import PgVectorSearchRepository

pytestmark = pytest.mark.integration

class FakeReranker:
    def rerank(self, *, query: str, results: list[SearchResult], limit: int) -> list[SearchResult]:
        return results[:limit]


class FakeLLMProvider:
    def __init__(self, reply: str) -> None:
        self._reply = reply
        self.last_system: str = ""
        self.last_messages: list[dict[str, str]] = []

    async def stream(self, *, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        self.last_system = system
        self.last_messages = messages
        yield self._reply


@pytest.fixture(scope="module")
def pg_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(image="pgvector/pgvector:pg16", driver="asyncpg") as container:
        yield container


@pytest.fixture(scope="module")
def es_container() -> Iterator[ElasticSearchContainer]:
    with ElasticSearchContainer("docker.elastic.co/elasticsearch/elasticsearch:8.15.0") as container:
        yield container


async def test_full_rag_flow_against_real_postgres_and_elasticsearch(
    pg_container: PostgresContainer, es_container: ElasticSearchContainer
) -> None:
    url = pg_container.get_connection_url()
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    es_host = es_container.get_container_host_ip()
    es_port = es_container.get_exposed_port(9200)
    indexer = ElasticsearchIndexer(url=f"http://{es_host}:{es_port}", index_name="rag-integration-test")

    session_local = async_sessionmaker(bind=engine, expire_on_commit=False)
    local_provider = LocalEmbeddingProvider()
    llm = FakeLLMProvider("A chunk is a small piece of a larger document.")

    async with session_local() as session:
        session.add(SourceModel(id="s1", workspace_id="w1", type="markdown", storage_key="w1/a.md"))
        await session.flush()
        session.add(DocumentModel(id="d1", source_id="s1", raw_text="irrelevant"))
        await session.flush()
        chunk_text = "A chunk is a small, overlapping piece of a larger document used for retrieval."
        embedding = local_provider.embed([chunk_text])[0]
        session.add(
            ChunkModel(
                id="c1", source_id="s1", document_id="d1", workspace_id="w1",
                order_index=0, text=chunk_text, embedding=embedding,
            )
        )
        await session.flush()
        seeded_chunks = await SqlAlchemyAsyncChunkRepository(session).get_by_ids(["c1"])
        indexer.index_chunks(seeded_chunks, source_type="markdown")
        indexer.refresh()

        inner = HybridSearchQueryHandler(
            indexer, PgVectorSearchRepository(session), local_provider, SqlAlchemyAsyncChunkRepository(session)
        )
        search_handler = RerankingSearchQueryHandler(inner, FakeReranker())

        conversations = SqlAlchemyAsyncConversationRepository(session)
        messages = SqlAlchemyAsyncMessageRepository(session)

        create_handler = CreateConversationCommandHandler(conversations)
        conversation_id = await create_handler.handle(CreateConversationCommand(workspace_id="w1", user_id="u1"))

        send_handler = SendUserMessageCommandHandler(conversations, messages)
        await send_handler.handle(
            SendUserMessageCommand(
                conversation_id=conversation_id, requesting_user_id="u1", content="what is a chunk?"
            )
        )

        reply_service = GenerateAssistantReplyService(conversations, messages, search_handler, llm)
        deltas = [
            d async for d in reply_service.stream(conversation_id=conversation_id, workspace_id="w1")
        ]

        assert deltas == ["A chunk is a small piece of a larger document."]
        history = await messages.list_by_conversation_id(conversation_id)
        assert len(history) == 2
        assert history[1].source_chunk_ids == ["c1"]
        assert "retrieval" in llm.last_system

    await engine.dispose()
