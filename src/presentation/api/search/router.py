import os

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.search.queries import SearchQuery
from application.search.query_handlers import HybridSearchQueryHandler, RerankingSearchQueryHandler
from domain.workspaces.entities import Permission, Role
from infrastructure.database.session import get_db
from infrastructure.ingestion.async_repository import SqlAlchemyAsyncChunkRepository
from infrastructure.ingestion.embeddings.local_provider import LocalEmbeddingProvider
from infrastructure.ingestion.embeddings.openai_provider import OpenAIEmbeddingProvider
from infrastructure.ingestion.search_index import ElasticsearchIndexer
from infrastructure.search.reranker import CrossEncoderReranker
from infrastructure.search.vector_search import PgVectorSearchRepository
from presentation.api.search.schemas import SearchResultResponse
from presentation.api.workspaces.dependencies import require_permission

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/search", tags=["search"])

_keyword_search = ElasticsearchIndexer(url=os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))
_embedding_provider = (
    OpenAIEmbeddingProvider()
    if os.environ.get("EMBEDDING_PROVIDER", "local") == "openai"
    else LocalEmbeddingProvider(device=os.environ.get("EMBEDDING_DEVICE", "cpu"))
)
_reranker = CrossEncoderReranker(device=os.environ.get("RERANKER_DEVICE", "cpu"))


def get_search_handler(session: AsyncSession = Depends(get_db)) -> RerankingSearchQueryHandler:
    inner = HybridSearchQueryHandler(
        _keyword_search,
        PgVectorSearchRepository(session),
        _embedding_provider,
        SqlAlchemyAsyncChunkRepository(session),
    )
    return RerankingSearchQueryHandler(inner, _reranker)


@router.get("", response_model=list[SearchResultResponse])
async def search(
    workspace_id: str,
    q: str = Query(..., min_length=1),
    source_type: str | None = Query(None, pattern="^(pdf|markdown)$"),
    limit: int = Query(10, ge=1, le=50),
    _role: Role = Depends(require_permission(Permission.VIEW_WORKSPACE)),
    handler: RerankingSearchQueryHandler = Depends(get_search_handler),
) -> list[SearchResultResponse]:
    results = await handler.handle(
        SearchQuery(query=q, workspace_id=workspace_id, source_type=source_type, limit=limit)
    )
    return [
        SearchResultResponse(chunk_id=r.chunk_id, source_id=r.source_id, text=r.text, score=r.score)
        for r in results
    ]
