import pytest

from eval.metrics import aggregate, evaluate_query, list_exhausted


def hits(*docs):
    return [{"_id": f"c{i}", "doc_id": d} for i, d in enumerate(docs)]


def test_recall_and_rr_are_computed_on_distinct_docs():
    # three chunks of 'a' then 'b': 'b' is rank 2 by doc, not rank 4
    row = evaluate_query(hits("a", "a", "a", "b", "c"), ["b"], window=200)
    assert row["recall@5"] == 1.0 and row["rr"] == 0.5 and row["distinct_docs"] == 3


def test_recall_with_several_expected_docs_and_cutoffs():
    h = hits(*"abcdefgh", "x", "y", "z")
    row = evaluate_query(h, ["a", "f", "z"], window=200)
    assert row["recall@5"] == pytest.approx(1 / 3) and row["recall@10"] == pytest.approx(2 / 3) and row["rr"] == 1.0


def test_exhausted_query_stays_in_recall_as_a_miss():
    ex = evaluate_query(hits("a", "b"), ["zzz"], window=200)  # only 2 chunks matched at all: list exhausted
    ok = evaluate_query(hits(*"abcdefghij"), ["a"], window=10)  # full window returned, expected doc found
    assert ex["exhausted"] and ex["recall@10"] == 0.0 and ex["rr"] == 0.0
    agg = aggregate([ex, ok])
    assert agg["n"] == 2 and agg["recall@10"] == 0.5 and agg["mrr"] == 0.5  # the exhausted miss is NOT dropped
    assert agg["exhausted"] == 1 and agg["exhausted_share"] == 0.5 and agg["exhausted_missed"] == 1


def test_exhausted_query_that_still_finds_its_doc_counts_as_a_hit_and_as_exhausted():
    row = evaluate_query(hits("a", "b"), ["a"], window=200)
    agg = aggregate([row])
    assert agg["recall@5"] == 1.0 and agg["exhausted"] == 1 and agg["exhausted_missed"] == 0


def test_short_counts_any_list_with_fewer_than_ten_distinct_docs():
    full = evaluate_query(hits(*"abcdefghij"), ["a"], window=10)
    short_not_exhausted = evaluate_query(hits(*"aaaaaaaaaab"), ["a"], window=10)  # window full, but only 2 docs
    agg = aggregate([full, short_not_exhausted])
    assert agg["short"] == 1 and agg["exhausted"] == 0


def test_list_exhausted_boundary_and_empty_results():
    assert list_exhausted(hits("a"), window=2) and not list_exhausted(hits("a", "b"), window=2)
    row = evaluate_query([], ["a"], window=200)
    assert row["exhausted"] and row["recall@5"] == 0.0 and row["rr"] == 0.0 and row["distinct_docs"] == 0


def test_unanswerable_questions_have_no_retrieval_metrics_and_empty_aggregate_is_safe():
    with pytest.raises(ValueError):
        evaluate_query(hits("a"), [])
    assert aggregate([]) == {"n": 0}
