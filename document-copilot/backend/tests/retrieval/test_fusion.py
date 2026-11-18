from uuid import UUID

import pytest

from app.retrieval.fusion import reciprocal_rank_fusion


def ids(n: int) -> list[UUID]:
    return [UUID(int=i) for i in range(1, n + 1)]


def test_a_chunk_found_by_both_searches_beats_one_found_by_one():
    a, b, c = ids(3)
    # a is only 3rd in the first list but also in the second; b wins the first list alone.
    fused = reciprocal_rank_fusion([[b, c, a], [a]])
    assert next(chunk for chunk, _ in fused) == a


def test_scores_are_the_sum_of_one_over_k_plus_rank():
    a, b = ids(2)
    scores = dict(reciprocal_rank_fusion([[a, b], [a]], k=60))
    assert scores[a] == pytest.approx(1 / 61 + 1 / 61)
    assert scores[b] == pytest.approx(1 / 62)


def test_chunks_found_by_only_one_search_are_still_returned():
    a, b = ids(2)
    fused = reciprocal_rank_fusion([[a], [b]])
    assert {chunk for chunk, _ in fused} == {a, b}


def test_a_single_list_keeps_its_order():
    a, b, c = ids(3)
    assert [chunk for chunk, _ in reciprocal_rank_fusion([[a, b, c]])] == [a, b, c]


def test_empty_input_gives_empty_output():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_equal_scores_are_ordered_the_same_way_every_time():
    a, b = ids(2)
    # Both rank 1 in one list each: identical score, so id decides.
    assert reciprocal_rank_fusion([[b], [a]]) == reciprocal_rank_fusion([[a], [b]])
    assert [chunk for chunk, _ in reciprocal_rank_fusion([[b], [a]])] == [a, b]


def test_worked_values_from_the_plan():
    a = ids(1)[0]
    assert dict(reciprocal_rank_fusion([[a]]))[a] == pytest.approx(0.0164, abs=1e-4)
    assert dict(reciprocal_rank_fusion([[a], [a]]))[a] == pytest.approx(
        0.0328, abs=1e-4
    )
