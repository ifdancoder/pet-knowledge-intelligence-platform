from application.search.queries import SearchQuery
from application.search.query_handlers import HybridSearchQueryHandler, RerankingSearchQueryHandler
from domain.ingestion.entities import Chunk
from domain.search.entities import SearchResult


class FakeKeywordSearch:
    def __init__(self, hits: list[dict]) -> None:
        self._hits = hits
        self.last_call: dict | None = None

    def search(self, *, query: str, workspace_id: str, source_type: str | None, limit: int) -> list[dict]:
        self.last_call = {
            "query": query, "workspace_id": workspace_id, "source_type": source_type, "limit": limit
        }
        return self._hits


class FakeVectorSearch:
    def __init__(self, hits: list[dict]) -> None:
        self._hits = hits

    async def search(
        self, *, query_embedding: list[float], workspace_id: str, source_type: str | None, limit: int
    ) -> list[dict]:
        return self._hits


class FakeEmbeddingProvider:
    dimension = 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 2.0, 3.0, 4.0] for _ in texts]


class FakeChunkRepository:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks_by_id = {c.id: c for c in chunks}

    async def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        return [self._chunks_by_id[c] for c in chunk_ids if c in self._chunks_by_id]


class FakeReranker:
    def __init__(self) -> None:
        self.last_call: dict | None = None

    def rerank(self, *, query: str, results: list[SearchResult], limit: int) -> list[SearchResult]:
        self.last_call = {"query": query, "results": results, "limit": limit}
        return results[:limit]


async def test_hybrid_handler_fuses_and_hydrates_chunk_text() -> None:
    chunks = [
        Chunk(id="c1", source_id="s1", document_id="d1", workspace_id="w1", order_index=0, text="hello"),
        Chunk(id="c2", source_id="s2", document_id="d2", workspace_id="w1", order_index=0, text="world"),
    ]
    handler = HybridSearchQueryHandler(
        FakeKeywordSearch([{"chunk_id": "c1", "score": 9.0}]),
        FakeVectorSearch([{"chunk_id": "c2", "score": 0.9}]),
        FakeEmbeddingProvider(),
        FakeChunkRepository(chunks),
    )

    results = await handler.handle(SearchQuery(query="hi", workspace_id="w1", source_type=None, limit=10))

    assert {r.chunk_id for r in results} == {"c1", "c2"}
    assert next(r.text for r in results if r.chunk_id == "c1") == "hello"


async def test_hybrid_handler_fetches_at_least_the_candidate_pool_size() -> None:
    keyword_search = FakeKeywordSearch([])
    handler = HybridSearchQueryHandler(
        keyword_search, FakeVectorSearch([]), FakeEmbeddingProvider(), FakeChunkRepository([])
    )

    await handler.handle(SearchQuery(query="hi", workspace_id="w1", source_type=None, limit=3))

    assert keyword_search.last_call is not None
    assert keyword_search.last_call["limit"] == 20  # max(limit=3, _CANDIDATE_POOL_SIZE=20)


async def test_hybrid_handler_forwards_source_type_filter() -> None:
    keyword_search = FakeKeywordSearch([])
    handler = HybridSearchQueryHandler(
        keyword_search, FakeVectorSearch([]), FakeEmbeddingProvider(), FakeChunkRepository([])
    )

    await handler.handle(SearchQuery(query="hi", workspace_id="w1", source_type="pdf", limit=10))

    assert keyword_search.last_call["source_type"] == "pdf"


async def test_reranking_handler_delegates_to_inner_then_reranks() -> None:
    chunk = Chunk(id="c1", source_id="s1", document_id="d1", workspace_id="w1", order_index=0, text="hello")
    inner = HybridSearchQueryHandler(
        FakeKeywordSearch([{"chunk_id": "c1", "score": 9.0}]),
        FakeVectorSearch([]),
        FakeEmbeddingProvider(),
        FakeChunkRepository([chunk]),
    )
    reranker = FakeReranker()
    handler = RerankingSearchQueryHandler(inner, reranker)

    query = SearchQuery(query="hi", workspace_id="w1", source_type=None, limit=1)
    results = await handler.handle(query)

    assert reranker.last_call is not None
    assert reranker.last_call["limit"] == 1
    assert len(results) == 1
    assert results[0].chunk_id == "c1"
