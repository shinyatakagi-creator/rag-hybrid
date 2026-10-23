import json
from pathlib import Path

import pytest

from eval import checkpoint4_round3 as r3
from eval.checkpoint4_round3 import KEYS, ITEMS, KEY, PRACTICE, _norm, labelled, run_label, run_practice

needs_build = pytest.mark.skipif(not (ITEMS.exists() and KEY.exists() and PRACTICE.exists()), reason="round 3 not built")


def scripted(answers):
    it = iter(answers)
    shown = []
    return (lambda prompt="": next(it)), shown.append, shown


def toy_items(n=3):
    return [{"id": f"id{i}", "sentence": f"sentence {i}", "excerpt": f"excerpt {i}"} for i in range(n)]


def test_labelling_writes_labels_notes_and_resumes_after_quit(tmp_path):
    log = tmp_path / "labels.jsonl"
    inp, out, shown = scripted(["s", "first note", "u", "", "q"])
    assert run_label(toy_items(), log, inp, out) is False  # quit on item 3
    assert [(a["id"], a["label"], a["note"]) for a in labelled(r3._read_log(log))] == [("id0", "supported", "first note"), ("id1", "unsupported", "")]
    inp, out, shown = scripted(["p", ""])
    assert run_label(toy_items(), log, inp, out) is True  # resumes at item 3 only
    assert [a["label"] for a in labelled(r3._read_log(log))] == ["supported", "unsupported", "partial"]
    assert "Item 3 of 3" in "\n".join(shown) and "Item 1 of 3" not in "\n".join(shown)


def test_undo_removes_the_last_answer_and_asks_again(tmp_path):
    log = tmp_path / "labels.jsonl"
    inp, out, shown = scripted(["s", "", "u", "", "z", "p", "", "u", ""])  # label, label, undo item 2, relabel it, label item 3
    assert run_label(toy_items(), log, inp, out) is True
    assert [(a["id"], a["label"]) for a in labelled(r3._read_log(log))] == [("id0", "supported"), ("id1", "partial"), ("id2", "unsupported")]
    assert sum(1 for r in r3._read_log(log) if r.get("undo")) == 1


def test_invalid_keys_are_rejected_and_undo_is_not_offered_first(tmp_path):
    inp, out, shown = scripted(["z", "x", "q"])
    run_label(toy_items(), tmp_path / "l.jsonl", inp, out)
    text = "\n".join(shown)
    assert "Please answer s, p, u or q." in text and "undo" not in text.split("Please answer")[0].split("> ")[0]


def test_nothing_displayed_or_logged_reveals_verdicts_configs_or_controls(tmp_path):
    log = tmp_path / "labels.jsonl"
    inp, out, shown = scripted(["s", "", "p", "", "u", ""])
    run_label(toy_items(), log, inp, out)
    blob = ("\n".join(shown) + log.read_text()).lower()
    for word in ("control", "verifier", "heading/", "hybrid", "dense", "yes_pair", "mutation", "known-wrong"):
        assert word not in blob


def test_practice_shows_the_expected_label_after_each_answer_and_resumes(tmp_path):
    prac = [{"id": f"pr-{i}", "sentence": "s", "excerpt": "e", "expected": "supported" if i % 2 else "unsupported", "reason": f"because {i}"} for i in range(1, 4)]
    log = tmp_path / "p.jsonl"
    inp, out, shown = scripted(["s", "", "u", "", "q"])
    assert run_practice(prac, log, inp, out) is False
    text = "\n".join(shown)
    assert "Expected: supported. because 1  (matches your answer)" in text and "Expected: unsupported. because 2  (matches your answer)" in text
    inp, out, shown = scripted(["u", ""])
    assert run_practice(prac, log, inp, out) is True and "because 3" in "\n".join(shown) and "differs from your answer" in "\n".join(shown)


@needs_build
def test_built_sets_are_disjoint_and_have_the_right_shape():
    from eval.checkpoint4_round2 import control_items as r2_controls
    items, prac, key = json.loads(ITEMS.read_text()), json.loads(PRACTICE.read_text()), json.loads(KEY.read_text())["items"]
    assert len(items) == 30 and len(prac) == 6 and set(key) == {i["id"] for i in items}
    kinds = [v["kind"] for v in key.values()]
    assert kinds.count("yes_pair") == 24 and kinds.count("control_wrong") == 3 and kinds.count("control_correct") == 3
    assert sorted(v["subtype"] for v in key.values() if v["kind"] != "yes_pair") == sorted(["changed number", "inverted claim", "swapped citation", "verbatim", "faithful paraphrase", "faithful paraphrase"])
    # yes pairs not used in rounds 1 or 2
    keys, sents, _ = r3.used_before()
    used = {(v["config"], v["qid"], v["sentence_no"], v["citation"]) for v in key.values() if "config" in v}
    assert len(used) == 24 and not used & keys and all(v["verifier"] == "yes" for v in key.values() if "config" in v)
    # sentences and excerpts: scored vs practice vs round-2 controls
    scored_s, scored_e = {i["sentence"] for i in items}, {_norm(i["excerpt"]) for i in items}
    prac_s, prac_e = {p["sentence"] for p in prac}, {_norm(p["excerpt"]) for p in prac}
    r2_s, r2_e = {c["sentence"] for c in r2_controls()}, {_norm(c["excerpt"]) for c in r2_controls()}
    assert not scored_s & prac_s and not scored_e & prac_e
    assert not scored_s & r2_s and not scored_e & r2_e and not scored_s & sents
    ctl_s = {i["sentence"] for i, v in zip(items, key.values()) if v["kind"] != "yes_pair"}
    assert not prac_s & r2_s and not ctl_s & r2_s and len(ctl_s) == 6
    # the practice set covers the requested kinds and carries expected labels
    assert {p["kind"] for p in prac} >= {"changed number", "inverted claim", "swapped citation", "verbatim", "faithful paraphrase"}
    assert all(p["expected"] in KEYS.values() for p in prac)
    # the items file itself carries nothing but id, sentence, excerpt
    assert all(set(i) == {"id", "sentence", "excerpt"} for i in items)


@needs_build
def test_control_expectations_are_checked_against_the_excerpts():
    cs = {c["source"]: c for c in r3.control_excerpts()}
    ex = {k: _norm(c["excerpt"]) for k, c in cs.items()}
    assert _norm(cs["K4"]["sentence"]).rstrip(".") in ex["K4"]  # verbatim
    assert "let B use 10GiB and 4 cores" in ex["K1"] and "8 cores" not in ex["K1"]  # the number in the sentence is not the excerpt's
    assert "Expired tokens are rejected when used for authentication" in ex["K2"]  # the sentence says the opposite
    assert _norm(cs["K3"]["sentence"]).rstrip(".") not in ex["K3"] and "kubeadm" not in ex["K3"] and "admin.conf" not in ex["K3"]  # swapped: absent
    for k in ("K5", "K6"):
        assert cs[k]["expected"] == "supported"


def test_score_refuses_until_all_labelled(tmp_path, monkeypatch):
    items = toy_items(2)
    monkeypatch.setattr(r3, "ITEMS", tmp_path / "items.json")
    monkeypatch.setattr(r3, "LABEL_LOG", tmp_path / "l.jsonl")
    monkeypatch.setattr(r3, "KEY", tmp_path / "key.json")
    (tmp_path / "items.json").write_text(json.dumps(items))
    (tmp_path / "l.jsonl").write_text(json.dumps({"id": "id0", "label": "supported", "note": ""}) + "\n")
    assert r3.run_score() == 1
