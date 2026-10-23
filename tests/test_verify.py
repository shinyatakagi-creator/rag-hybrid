import json
from pathlib import Path

import pytest

from eval.verify_mutation import CONTROLS, MUTATIONS, PARAPHRASES, build
from ingest.embed_cache import BudgetExceeded, SpendGuard
from rag.verify import (
    InvalidVerdicts, build_message, derive_verdict, load_row_chunks, pairs_of, summarize, validate_verdicts, verify_answer,
)

MODEL = "claude-haiku-5-5"
SENTS = [{"sentence": "A is 5.", "citations": [1, 2]}, {"sentence": "B holds.", "citations": [2]}, {"sentence": "C.", "citations": [1, 1]}]
CHUNKS = {1: "chunk one text", 2: "chunk two text"}


CLAIMS = {"yes": ["supported"], "partial": ["supported", "unsupported"], "no": ["contradicted"]}


def raw(s, c, v="yes", r="because"):
    """What the model returns: claim statuses and a reason, no verdict."""
    return {"sentence": s, "citation": c, "claims": [{"claim": f"claim {i}", "status": st} for i, st in enumerate(CLAIMS[v])], "reason": r}


def j(s, c, v="yes", r="because"):
    """A judgement as validate_verdicts returns it: with the derived verdict."""
    return {**raw(s, c, v, r), "verdict": v}


def test_pairs_are_one_per_distinct_citation_numbered_from_one():
    assert pairs_of(SENTS) == [(1, 1), (1, 2), (2, 2), (3, 1)]
    assert pairs_of([{"sentence": "refusal", "citations": []}]) == []


def test_message_has_only_cited_excerpts_and_lists_every_pair():
    msg = build_message(SENTS, {1: "one", 2: "two", 3: "NEVER CITED"})
    assert "[Excerpt 1]\none" in msg and "[Excerpt 2]\ntwo" in msg and "NEVER CITED" not in msg
    assert "- sentence 1 vs excerpt 2" in msg and "Sentence 2: B holds." in msg


def test_valid_verdicts_come_back_in_expected_pair_order():
    expected = pairs_of(SENTS)
    shuffled = {"judgements": [raw(3, 1), raw(1, 2, "no"), raw(1, 1), raw(2, 2, "partial")]}
    out = validate_verdicts(shuffled, expected)
    assert [(x["sentence"], x["citation"]) for x in out] == expected
    assert [x["verdict"] for x in out] == ["yes", "no", "partial", "yes"]  # derived in code from the claim statuses


def st(*statuses):
    return [{"claim": f"c{i}", "status": s} for i, s in enumerate(statuses)]


@pytest.mark.parametrize("statuses,verdict", [
    (["supported"], "yes"),
    (["supported", "supported", "supported"], "yes"),
    (["supported", "unsupported"], "partial"),
    (["unsupported", "supported", "unsupported"], "partial"),
    (["unsupported"], "no"),
    (["unsupported", "unsupported"], "no"),
    (["contradicted"], "no"),
    (["supported", "contradicted"], "no"),             # one contradiction outweighs any number of supported claims
    (["supported", "unsupported", "contradicted"], "no"),
])
def test_verdict_is_derived_from_claim_statuses_by_the_rule(statuses, verdict):
    assert derive_verdict(st(*statuses)) == verdict


def test_the_model_cannot_supply_its_own_verdict():
    bad = {"judgements": [{**raw(1, 1), "verdict": "yes"}, raw(1, 2), raw(2, 2), raw(3, 1)]}
    with pytest.raises(InvalidVerdicts):
        validate_verdicts(bad, pairs_of(SENTS))


@pytest.mark.parametrize("bad", [
    {"judgements": [raw(1, 1), raw(1, 2), raw(2, 2)]},                               # pair (3,1) missing
    {"judgements": [raw(1, 1), raw(1, 2), raw(2, 2), raw(3, 1), raw(9, 9)]},         # unexpected pair
    {"judgements": [raw(1, 1), raw(1, 1), raw(1, 2), raw(2, 2), raw(3, 1)]},         # duplicate pair
    {"judgements": [{**raw(1, 1), "claims": []}, raw(1, 2), raw(2, 2), raw(3, 1)]},  # no claims listed
    {"judgements": [{**raw(1, 1), "claims": st("maybe")}, raw(1, 2), raw(2, 2), raw(3, 1)]},  # status outside the enum
    {"judgements": [{**raw(1, 1), "claims": [{"claim": " ", "status": "supported"}]}, raw(1, 2), raw(2, 2), raw(3, 1)]},  # blank claim
    {"judgements": [{**raw(1, 1), "claims": [{"claim": "x"}]}, raw(1, 2), raw(2, 2), raw(3, 1)]},  # claim without status
    {"judgements": [raw(1, 1, r=" "), raw(1, 2), raw(2, 2), raw(3, 1)]},             # empty reason
    {"judgements": [{**raw(1, 1), "sentence": "1"}, raw(1, 2), raw(2, 2), raw(3, 1)]},  # sentence not an int
    {"judgements": [{**raw(1, 1), "extra": 1}, raw(1, 2), raw(2, 2), raw(3, 1)]},    # extra key
    {"nope": []}, [],
])
def test_malformed_verdicts_are_rejected(bad):
    with pytest.raises(InvalidVerdicts):
        validate_verdicts(bad, pairs_of(SENTS))


def test_summary_precision_and_unsupported_vs_partial_sentences():
    sents = [{"sentence": "S1", "citations": [1]}, {"sentence": "S2", "citations": [1, 2]}, {"sentence": "S3", "citations": [2]}, {"sentence": "S4", "citations": [1]}]
    js = [j(1, 1, "yes"), j(2, 1, "no"), j(2, 2, "yes"), j(3, 2, "no"), j(4, 1, "partial")]
    s = summarize(sents, js)
    assert (s["yes"], s["partial"], s["no"], s["citations"]) == (2, 1, 2, 5) and s["citation_precision"] == pytest.approx(0.4)
    assert [u["sentence"] for u in s["unsupported_sentences"]] == [3]          # only 'no' verdicts
    assert [u["sentence"] for u in s["partially_supported_sentences"]] == [4]   # best verdict is partial
    assert summarize([{"sentence": "x", "citations": []}], [])["citation_precision"] is None


class Block:
    def __init__(self, t): self.type, self.text = "text", t


class FakeHaiku:
    def __init__(self, payload, stop="end_turn", usage=(2000, 300)):
        self.calls, self.kw, self.payload, self.stop, self.usage = 0, None, payload, stop, usage
        self.messages = self

    def create(self, **kw):
        self.calls, self.kw = self.calls + 1, kw
        u = type("U", (), {"input_tokens": self.usage[0], "output_tokens": self.usage[1]})()
        txt = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return type("R", (), {"content": [Block(txt)], "usage": u, "stop_reason": self.stop})()


GOOD = {"judgements": [raw(1, 1), raw(1, 2, "partial"), raw(2, 2, "no"), raw(3, 1)]}


def test_verify_answer_cost_from_usage_and_request_shape():
    client, guard = FakeHaiku(GOOD, usage=(1_000_000, 100_000)), SpendGuard(10)
    r = verify_answer(client, guard, MODEL, SENTS, CHUNKS)
    assert r["cost_usd"] == pytest.approx(0.10 + 0.05) and guard.spent == pytest.approx(r["cost_usd"])
    assert client.kw["model"] == MODEL and client.kw["output_config"]["format"]["type"] == "json_schema"
    assert not {"temperature", "top_p", "top_k", "tool_choice"} & set(client.kw)
    assert r["summary"]["citation_precision"] == 0.5


def test_refusal_has_nothing_to_verify_and_makes_no_call():
    client = FakeHaiku(GOOD)
    r = verify_answer(client, SpendGuard(5), MODEL, [{"sentence": "No docs.", "citations": []}], {})
    assert r["pairs"] == 0 and client.calls == 0


def test_spend_guard_and_dry_run_and_decline_make_no_call():
    c = FakeHaiku(GOOD)
    with pytest.raises(BudgetExceeded):
        verify_answer(c, SpendGuard(1e-9), MODEL, SENTS, CHUNKS)
    assert verify_answer(c, SpendGuard(5), MODEL, SENTS, CHUNKS, dry_run=True)["estimate"]["worst_case_cost"] > 0
    with pytest.raises(SystemExit):
        verify_answer(c, SpendGuard(5), MODEL, SENTS, CHUNKS, confirm=lambda e: False)
    assert c.calls == 0


@pytest.mark.parametrize("payload,stop", [("not json", "end_turn"), ({"judgements": []}, "end_turn"), (GOOD, "max_tokens")])
def test_bad_verifier_output_is_rejected_but_billed(payload, stop):
    guard = SpendGuard(5)
    with pytest.raises(InvalidVerdicts):
        verify_answer(FakeHaiku(payload, stop=stop), guard, MODEL, SENTS, CHUNKS)
    assert guard.spent > 0


def test_missing_excerpt_text_is_an_error_before_any_call():
    c = FakeHaiku(GOOD)
    with pytest.raises(InvalidVerdicts, match="no excerpt text"):
        verify_answer(c, SpendGuard(5), MODEL, SENTS, {1: "only one"})
    assert c.calls == 0


def test_row_chunks_prefer_stored_content_then_snapshot():
    row = {"chunks": [{"n": 1, "chunk_id": "a", "content": "stored"}, {"n": 2, "chunk_id": "b"}]}
    assert load_row_chunks(row, {"b": {"content": "from snapshot"}}) == {1: "stored", 2: "from snapshot"}


@pytest.mark.skipif(not Path("eval/results/generation_log.jsonl").exists(), reason="no saved answers")
def test_mutations_apply_to_the_saved_answers_and_actually_change_something():
    rows = [json.loads(l) for l in open("eval/results/generation_log.jsonl")]
    by_row = build(rows)
    items = [m for v in by_row.values() for m in v]
    wrong = [m for m in items if m["kind"] in ("swap", "text")]
    verb = [m for m in items if m["kind"] == "control_verbatim"]
    para = [m for m in items if m["kind"] == "control_paraphrase"]
    assert len(wrong) == len(MUTATIONS) == 10 and len(verb) == len(CONTROLS) == 5 and len(para) == len(PARAPHRASES) == 10
    assert sum(m["kind"] == "swap" for m in wrong) == 5 and len(items) == 25
    for m in wrong:
        if m["kind"] == "swap":
            assert m["sentence"] == m["orig_sentence"] and m["citations"] != m["orig_citations"]
        else:
            assert m["sentence"] != m["orig_sentence"] and m["citations"] == m["orig_citations"]
    for m in verb + para:  # controls are unchanged
        assert m["sentence"] == m["orig_sentence"] and m["citations"] == m["orig_citations"]
    assert [m["id"] for m in by_row[0]] != sorted(m["id"] for m in by_row[0])  # shuffled, not grouped by kind


@pytest.mark.skipif(not Path("eval/results/context_snapshot.json").exists(), reason="no snapshot")
def test_authored_controls_are_verbatim_from_their_cited_chunk():
    import re
    rows = [json.loads(l) for l in open("eval/results/generation_log.jsonl")]
    snap = json.load(open("eval/results/context_snapshot.json"))["chunks"]
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower().replace("`", "")))
    for cid, kind, ri, si, text, cites in CONTROLS:
        if si is not None:  # a saved model sentence, not authored
            continue
        chunk = snap[rows[ri]["chunks"][cites[0] - 1]["chunk_id"]]["content"]
        assert norm(text) in norm(chunk), f"{cid} is not literally in chunk [{cites[0]}]"


@pytest.mark.skipif(not Path("eval/results/context_snapshot.json").exists(), reason="no snapshot")
def test_paraphrased_controls_are_really_paraphrases_not_copies():
    import re
    rows = [json.loads(l) for l in open("eval/results/generation_log.jsonl")]
    snap = json.load(open("eval/results/context_snapshot.json"))["chunks"]
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower().replace("`", "")))
    for pid, ri, text, cites in PARAPHRASES:
        chunk = snap[rows[ri]["chunks"][cites[0] - 1]["chunk_id"]]["content"]
        assert norm(text) not in norm(chunk), f"{pid} is a verbatim copy, not a paraphrase"
