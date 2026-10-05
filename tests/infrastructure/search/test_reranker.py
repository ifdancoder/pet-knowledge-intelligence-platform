from unittest.mock import patch

from domain.search.entities import SearchResult
from infrastructure.search.reranker import CrossEncoderReranker


def test_reranker_defaults_to_cpu() -> None:
    with patch("infrastructure.search.reranker.CrossEncoder") as mock_cls:
        CrossEncoderReranker()
        mock_cls.assert_called_once_with("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")


def test_reranker_forwards_an_explicit_device() -> None:
    with patch("infrastructure.search.reranker.CrossEncoder") as mock_cls:
        CrossEncoderReranker(device="cuda")
        mock_cls.assert_called_once_with("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cuda")


def test_rerank_orders_relevant_text_above_irrelevant_text() -> None:
    reranker = CrossEncoderReranker()
    results = [
        SearchResult(chunk_id="irrelevant", source_id="s1", text="the weather in paris is sunny today", score=0.5),
        SearchResult(chunk_id="relevant", source_id="s1", text="python list comprehensions explained", score=0.5),
    ]

    reranked = reranker.rerank(query="how do python list comprehensions work", results=results, limit=2)

    assert reranked[0].chunk_id == "relevant"


def test_rerank_respects_limit() -> None:
    reranker = CrossEncoderReranker()
    results = [
        SearchResult(chunk_id=f"c{i}", source_id="s1", text=f"text number {i}", score=0.5) for i in range(5)
    ]

    assert len(reranker.rerank(query="text", results=results, limit=2)) == 2


def test_rerank_handles_an_empty_list() -> None:
    reranker = CrossEncoderReranker()
    assert reranker.rerank(query="anything", results=[], limit=10) == []
