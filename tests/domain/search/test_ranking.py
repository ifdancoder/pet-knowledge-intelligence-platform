from domain.search.ranking import reciprocal_rank_fusion


def test_fuses_two_disjoint_lists_preserving_both() -> None:
    keyword_hits = [{"chunk_id": "a", "score": 9.1}, {"chunk_id": "b", "score": 3.2}]
    vector_hits = [{"chunk_id": "c", "score": 0.95}, {"chunk_id": "d", "score": 0.80}]

    fused = reciprocal_rank_fusion(keyword_hits=keyword_hits, vector_hits=vector_hits)

    assert {chunk_id for chunk_id, _ in fused} == {"a", "b", "c", "d"}


def test_a_chunk_ranked_first_in_both_lists_wins() -> None:
    keyword_hits = [{"chunk_id": "a", "score": 9.1}, {"chunk_id": "b", "score": 3.2}]
    vector_hits = [{"chunk_id": "a", "score": 0.95}, {"chunk_id": "c", "score": 0.80}]

    fused = reciprocal_rank_fusion(keyword_hits=keyword_hits, vector_hits=vector_hits)

    assert fused[0][0] == "a"


def test_ignores_the_input_lists_own_scores_only_rank_matters() -> None:
    # "b" is ranked #1 in vector_hits despite a tiny raw score — RRF must still favor it
    # over "a", which is ranked #2 in both lists, proving fusion uses rank, not magnitude.
    keyword_hits = [{"chunk_id": "a", "score": 9.1}, {"chunk_id": "x", "score": 8.0}]
    vector_hits = [{"chunk_id": "b", "score": 0.001}, {"chunk_id": "a", "score": 0.95}]

    fused = reciprocal_rank_fusion(keyword_hits=keyword_hits, vector_hits=vector_hits)
    ranking = [chunk_id for chunk_id, _ in fused]

    assert ranking.index("b") < ranking.index("x")


def test_empty_lists_produce_empty_result() -> None:
    assert reciprocal_rank_fusion(keyword_hits=[], vector_hits=[]) == []


def test_k_parameter_changes_the_fused_score_but_not_zero_results() -> None:
    hits = [{"chunk_id": "a", "score": 1.0}]
    low_k = reciprocal_rank_fusion(keyword_hits=hits, vector_hits=[], k=1)
    high_k = reciprocal_rank_fusion(keyword_hits=hits, vector_hits=[], k=1000)
    assert low_k[0][1] > high_k[0][1]
