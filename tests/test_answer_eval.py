import pytest

from eval.answer_eval import best_verdict_per_sentence, faithfulness, summarize_config


def J(s, c, v):
    return {"sentence": s, "citation": c, "verdict": v}


def row(id, typ, gold, outcome, judgements=(), verify_error=False, ctx=True):
    return {"id": id, "type": typ, "answerable": gold, "outcome": outcome, "verify_error": verify_error, "context_has_expected": ctx,
            "sentence_verdicts": list(best_verdict_per_sentence(list(judgements)).values()), "pair_verdicts": [j["verdict"] for j in judgements]}


def test_best_verdict_per_sentence_takes_the_strongest_citation():
    assert best_verdict_per_sentence([J(1, 1, "no"), J(1, 2, "yes"), J(2, 1, "partial"), J(2, 3, "no"), J(3, 1, "no")]) == {1: "yes", 2: "partial", 3: "no"}


def test_faithfulness_strict_lenient_and_citation_precision():
    qs = [row("a", "conceptual", True, "answered", [J(1, 1, "yes"), J(1, 2, "no"), J(2, 1, "partial"), J(3, 1, "no")])]
    f = faithfulness(qs)
    assert f["sentences"] == 3 and f["strict"] == pytest.approx(1 / 3) and f["lenient"] == pytest.approx(2 / 3)
    assert f["citations"] == 4 and f["citation_precision"] == 0.25
    assert faithfulness([])["strict"] is None  # no answered questions: no figure, not 0


def test_summary_counts_refusals_invalid_and_verification_errors_separately():
    rows = [row("e1", "exact_term", True, "answered", [J(1, 1, "yes")]), row("c1", "conceptual", True, "refused", ctx=False),
            row("m1", "mixed", True, "invalid"), row("m2", "mixed", True, "answered", verify_error=True),
            row("u1", "unanswerable", False, "refused"), row("u2", "unanswerable", False, "answered", [J(1, 1, "no")])]
    s = summarize_config(rows)
    assert (s["n_answerable"], s["n_unanswerable"]) == (4, 2)
    assert (s["correct_refusals"], s["answered_unanswerable"], s["false_refusals"]) == (1, 1, 1)
    assert s["invalid_answers"] == 1 and s["verification_errors"] == 1 and s["context_has_expected"] == "3 of 4"
    assert s["faithfulness_all_answered"]["questions"] == 2  # e1 and u2 (m2 had no verification, not silently counted)
    assert s["faithfulness_answerable_only"]["questions"] == 1
    assert s["by_type"]["conceptual"]["false_refusals"] == 1 and s["by_type"]["mixed"]["invalid"] == 1
