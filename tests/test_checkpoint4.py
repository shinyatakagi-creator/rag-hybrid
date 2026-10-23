import pytest

from eval.checkpoint4 import clopper_pearson, draw, score


def pairs():
    return [{"verifier": v, "sentence": f"s{i}", "excerpt": "x"} for i, v in enumerate(["yes"] * 40 + ["partial"] * 5 + ["no"] * 2)]


def test_draw_takes_every_non_yes_pair_and_a_seeded_sample_of_yes():
    p = pairs()
    s = draw(p, n_yes=10, seed=3)
    assert len(s) == 17 and sum(x["verifier"] != "yes" for x in s) == 7 and sum(x["verifier"] == "yes" for x in s) == 10
    assert [x["sentence"] for x in s] == [x["sentence"] for x in draw(p, n_yes=10, seed=3)]  # deterministic
    assert [x["sentence"] for x in s] != [x["sentence"] for x in draw(p, n_yes=10, seed=4)]
    assert [x["sentence"] for x in s[:7]] != sorted(x["sentence"] for x in s if x["verifier"] != "yes")  # shuffled, not non-yes first


def test_clopper_pearson_matches_known_values():
    lo, hi = clopper_pearson(0, 19)
    assert lo == 0.0 and hi == pytest.approx(0.1765, abs=1e-3)  # 1 - 0.025**(1/19)
    lo, hi = clopper_pearson(1, 19)
    assert (lo, hi) == pytest.approx((0.00133, 0.2603), abs=2e-3)
    assert clopper_pearson(19, 19)[1] == 1.0


def test_score_confusion_agreement_and_false_yes():
    items = {f"L{i}": {"verifier": v} for i, v in enumerate(["yes", "yes", "yes", "yes", "partial", "no"])}
    labels = dict(zip(items, ["supported", "supported", "partial", "unsupported", "partial", "supported"]))
    r = score(items, labels, {"yes": 40, "not_yes": 2})
    assert r["agreement_count"] == 3 and r["confusion_human_rows_verifier_columns"]["supported"] == {"supported": 2, "partial": 0, "unsupported": 1}
    assert r["false_yes_rate"]["k"] == 2 and r["false_yes_rate"]["n"] == 4 and r["false_yes_rate_unsupported_only"]["k"] == 1
    assert r["yes_stratum"] == {"n": 4, "agree": 2} and r["not_yes_stratum"] == {"n": 2, "agree": 1}
    with pytest.raises(ValueError):
        score(items, {**labels, "L0": "maybe"}, {"yes": 40, "not_yes": 2})
    with pytest.raises(ValueError):
        score(items, {k: v for k, v in labels.items() if k != "L0"}, {"yes": 40, "not_yes": 2})
