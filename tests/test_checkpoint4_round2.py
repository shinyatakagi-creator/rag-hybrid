import pytest

from eval.checkpoint4_round2 import control_items, draw, score


def yes(n):
    return [{"verifier": "yes", "config": "c", "qid": f"q{i}", "sentence_no": 1, "citation": 1, "sentence": f"s{i}", "excerpt": "x"} for i in range(n)]


def ctl():
    return [{"kind": "control_wrong", "source": f"M0{i}", "expected": "unsupported", "sentence": f"w{i}", "excerpt": "e"} for i in range(3)] + \
           [{"kind": "control_correct", "source": f"C0{i}", "expected": "supported", "sentence": f"r{i}", "excerpt": "e"} for i in range(3)]


def test_draw_has_24_yes_6_controls_deterministic_and_shuffled():
    s = draw(yes(100), ctl(), seed=5)
    assert len(s) == 30 and sum(p["kind"] == "yes_pair" for p in s) == 24 and sum(p["kind"] != "yes_pair" for p in s) == 6
    assert [p["sentence"] for p in s] == [p["sentence"] for p in draw(yes(100), ctl(), seed=5)]
    assert [p["kind"] for p in s][:6] != ["control_wrong"] * 3 + ["control_correct"] * 3


def items_and_labels(n_bad_controls, n_not_supported=0, n_unsupported=0):
    items = {f"M{i:02d}": {"kind": "yes_pair"} for i in range(1, 25)}
    items.update({f"M{25 + i:02d}": c for i, c in enumerate(ctl())})
    labels = {i: "supported" for i in items}
    for i in list(items)[:n_not_supported]:
        labels[i] = "partial"
    for i in list(items)[n_not_supported:n_not_supported + n_unsupported]:
        labels[i] = "unsupported"
    for j, i in enumerate([i for i, it in items.items() if it["kind"] != "yes_pair"]):
        labels[i] = it_expected = items[i]["expected"]
        if j < n_bad_controls:
            labels[i] = "partial"
    return items, labels


def test_one_bad_control_is_allowed_two_invalidate_the_round():
    items, labels = items_and_labels(1, n_not_supported=3, n_unsupported=2)
    r = score(items, labels)
    assert r["controls"]["valid_round"] and r["controls"]["mislabelled"] == 1
    v = r["verifier_yes_pairs"]
    assert v["n"] == 24 and v["false_yes_not_supported"]["k"] == 5 and v["false_yes_unsupported_only"]["k"] == 2
    lo, hi = v["false_yes_not_supported"]["ci95_exact"]
    assert 0 < lo < 5 / 24 < hi < 1
    items, labels = items_and_labels(2)
    r = score(items, labels)
    assert not r["controls"]["valid_round"] and "verifier_yes_pairs" not in r and "INVALID" in r["note"]
    with pytest.raises(ValueError):
        score(items, {**labels, "M01": "maybe"})


def test_controls_come_from_the_mutation_set_with_the_expected_labels():
    cs = control_items()
    assert [c["source"] for c in cs] == ["M01", "M06", "M10", "C02", "C04", "C05"]
    assert [c["expected"] for c in cs] == ["unsupported"] * 3 + ["supported"] * 3 and all(c["sentence"] and c["excerpt"] for c in cs)
