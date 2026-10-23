from eval.robustness_summary import slices_for, worst_slice


def row(**by):
    return {"by_type": {t: {"n": 4, "recall@10": r, "mrr": m} for t, (r, m) in by.items()}, "overall": {"n": 8, "recall@10": 0.5, "mrr": 0.4}}


def test_worst_slice_uses_recall_then_mrr_and_bare_term_comes_from_the_overall_row():
    s = slices_for(row(exact_term=(1.0, 0.9), conceptual=(0.5, 0.3)), row())
    assert set(s) == {"exact_term", "conceptual", "bare_term"} and s["bare_term"]["n"] == 8
    assert worst_slice(s) == "conceptual"
    assert worst_slice({"a": {"recall@10": 0.5, "mrr": 0.2}, "b": {"recall@10": 0.5, "mrr": 0.1}}) == "b"  # tie on recall: lower MRR
    assert "bare_term" not in slices_for(row(mixed=(1.0, 1.0)), None)
