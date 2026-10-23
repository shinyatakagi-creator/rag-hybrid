import pytest

from eval.retrieval_eval import bootstrap_ci, compare_ranks, doc_ranks, first_rank, format_md, paired, summarize, tiny_stats


def hits(*docs, tokens=200):
    return [{"_id": f"c{i}", "doc_id": d, "token_count": t if isinstance(t, int) else tokens} for i, (d, t) in enumerate((x if isinstance(x, tuple) else (x, tokens) for x in docs))]


def test_doc_ranks_are_over_distinct_docs_and_first_rank_is_the_best():
    r = doc_ranks(hits("a", "a", "b", "c", "b"), ["c", "b", "zzz"])
    assert r == {"c": 3, "b": 2, "zzz": None} and first_rank(r) == 2
    assert first_rank({"x": None}) is None


def test_compare_ranks_treats_a_missing_rank_as_worst():
    assert compare_ranks(2, 5) == "win" and compare_ranks(5, 2) == "loss" and compare_ranks(3, 3) == "tie"
    assert compare_ranks(7, None) == "win" and compare_ranks(None, 1) == "loss" and compare_ranks(None, None) == "tie"
    assert paired([1, None, 4, 2], [3, None, 1, 2]) == {"win": 1, "tie": 2, "loss": 1}


def test_bootstrap_is_deterministic_and_brackets_the_mean():
    v = [1.0, 0.0, 0.5, 1.0, 0.0, 0.25, 1.0, 0.0]
    lo, hi = bootstrap_ci(v, n_boot=2000)
    assert (lo, hi) == bootstrap_ci(v, n_boot=2000) and lo <= sum(v) / len(v) <= hi and 0 <= lo and hi <= 1
    assert bootstrap_ci([0.5] * 6, n_boot=200) == (0.5, 0.5)  # no variation, no interval


def test_tiny_stats_counts_top_chunks_only_and_expected_membership():
    q1 = (hits(("a", 50), ("b", 300), ("c", 60), "d", "e", ("a", 10)), ["a"])  # the tiny chunk at rank 6 is outside the top 5
    q2 = (hits(("x", 40), "y"), ["x", "zzz"])  # a short list: only 2 chunks counted
    s = tiny_stats([q1, q2])
    assert s["top_chunks"] == 7 and s["tiny"] == 3  # a50, c60, x40
    assert s["tiny_from_expected"] == 2 and s["questions_with_tiny_expected"] == 2 and s["tiny_from_expected_share"] == pytest.approx(2 / 3)


def test_summarize_includes_exhausted_miss_and_intervals():
    rows = [{"recall@5": 1.0, "recall@10": 1.0, "rr": 1.0, "distinct_docs": 12, "exhausted": False},
            {"recall@5": 0.0, "recall@10": 0.0, "rr": 0.0, "distinct_docs": 2, "exhausted": True}]
    s = summarize(rows)
    assert s["n"] == 2 and s["recall@10"] == 0.5 and s["exhausted"] == 1 and s["exhausted_missed"] == 1 and s["short"] == 1
    assert len(s["mrr_ci95"]) == 2 and format_md  # report formatter importable
