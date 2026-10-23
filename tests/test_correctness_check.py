import pytest

from eval.correctness_check import InvalidJudgement, build_message, is_clean, review_selection, validate


def J(cov="yes", con="no", reason="ok"):
    return {"key_facts_covered": cov, "contradicts_reference": con, "reason": reason}


def test_validate_accepts_only_the_exact_shape_and_enums():
    assert validate(J()) == J()
    for bad in (J(cov="maybe"), J(con="partial"), J(reason=" "), {"key_facts_covered": "yes"}, {**J(), "extra": 1}, "yes"):
        with pytest.raises(InvalidJudgement):
            validate(bad)


def test_message_hides_citations_and_excerpts():
    m = build_message("Q?", "REF", [{"sentence": "A one.", "citations": [1, 2]}, {"sentence": "A two.", "citations": [3]}])
    assert "Question: Q?" in m and "Reference answer: REF" in m and "A one. A two." in m and "[1" not in m and "citations" not in m


def test_review_selection_has_every_not_clean_row_plus_seeded_clean_sample():
    rows = [{"config": "c", "qid": f"q{i}", **J()} for i in range(10)] + [{"config": "c", "qid": "p1", **J(cov="partial")}, {"config": "c", "qid": "x1", **J(con="yes")}]
    sel = review_selection(rows, n_ok=3, seed=1)
    assert {"p1", "x1"} <= {r["qid"] for r in sel} and len(sel) == 5 and sum(is_clean(r) for r in sel) == 3
    assert [r["qid"] for r in sel] == [r["qid"] for r in review_selection(rows, n_ok=3, seed=1)]  # deterministic


def test_controls_apply_to_the_saved_answers_and_are_balanced():
    from pathlib import Path

    from eval.answer_eval import GEN_LOG, read_log
    from eval.correctness_check import CONTROLS, caught, control_targets
    from eval.retrieval_eval import load_golden
    if not Path(GEN_LOG).exists():
        pytest.skip("answer_eval logs not present")
    ts = control_targets(load_golden("eval/golden.jsonl"), read_log(GEN_LOG, lambda r: (r["config"], r["qid"])))
    assert [t["expected"] for t in ts].count("wrong") == 6 and [t["expected"] for t in ts].count("correct") == 2 and len(ts) == len(CONTROLS) == 8
    swapped = [t for t in ts if t["type"] == "swapped"]
    assert len(swapped) == 3 and all(t["question"] and t["sentences"][0]["sentence"] for t in swapped)
    assert caught(J(cov="no")) and caught(J(con="yes")) and not caught(J(cov="partial"))
