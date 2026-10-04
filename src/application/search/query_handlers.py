from starlette.concurrency import run_in_threadpool

from application.search.queries import SearchQuery
from domain.ingestion.ports import AsyncChunkRepository, EmbeddingProvider
from domain.search.entities import SearchResult
from domain.search.ports import KeywordSearchPort, Reranker, VectorSearchPort
from domain.search.ranking import reciprocal_rank_fusion

_CANDIDATE_POOL_SIZE = 20


class HybridSearchQueryHandler:
    def __init__(
        self,
        keyword_search: KeywordSearchPort,
        vector_search: VectorSearchPort,
        embedding_provider: EmbeddingProvider,
        chunks: AsyncChunkRepository,
    ) -> None:
        self._keyword_search = keyword_search
        self._vector_search = vector_search
        self._embedding_provider = embedding_provider
        self._chunks = chunks

    async def handle(self, query: SearchQuery) -> list[SearchResult]:
        pool_size = max(query.limit, _CANDIDATE_POOL_SIZE)

        keyword_hits = await run_in_threadpool(
            self._keyword_search.search,
            query=query.query,
            workspace_id=query.workspace_id,
            source_type=query.source_type,
            limit=pool_size,
        )
        query_embedding = (await run_in_threadpool(self._embedding_provider.embed, [query.query]))[0]
        vector_hits = await self._vector_search.search(
            query_embedding=query_embedding,
            workspace_id=query.workspace_id,
            source_type=query.source_type,
            limit=pool_size,
        )

        fused = reciprocal_rank_fusion(keyword_hits=keyword_hits, vector_hits=vector_hits)[:pool_size]
        chunk_ids = [chunk_id for chunk_id, _ in fused]
        chunks_by_id = {c.id: c for c in await self._chunks.get_by_ids(chunk_ids)}
        scores_by_id = dict(fused)

        return [
            SearchResult(
                chunk_id=chunk_id,
                source_id=chunks_by_id[chunk_id].source_id,
                text=chunks_by_id[chunk_id].text,
                score=scores_by_id[chunk_id],
            )
            for chunk_id in chunk_ids
            if chunk_id in chunks_by_id
        ]


class RerankingSearchQueryHandler:
    """Decorator — wraps any handler with the same handle(query) -> list[SearchResult]
    shape and reranks its output. HybridSearchQueryHandler never applies query.limit
    itself (it returns the whole candidate pool); this is the one place limit is enforced,
    after reranking has had the full pool to work with."""

    def __init__(self, inner: HybridSearchQueryHandler, reranker: Reranker) -> None:
        self._inner = inner
        self._reranker = reranker

    async def handle(self, query: SearchQuery) -> list[SearchResult]:
        candidates = await self._inner.handle(query)
        return self._reranker.rerank(query=query.query, results=candidates, limit=query.limit)
