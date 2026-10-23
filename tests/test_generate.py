import json

import pytest

from ingest.embed_cache import BudgetExceeded, SpendGuard
from rag.generate import (
    MAX_TOKENS, PRICES, InvalidAnswer, build_user_message, cost_usd, generate, select_context, validate_answer,
)

MODEL = "claude-sonnet-5-5"


def hit(i, doc):
    return {"chunk_id": f"c{i}", "_id": f"c{i}", "doc_id": doc, "heading_path": f"{doc} > h{i}", "url": f"https://k8s/{doc}/", "content": f"text {i}"}


# -- context cap ------------------------------------------------------------------------------
def test_context_caps_two_chunks_per_doc_keeps_rank_order_and_stops_at_eight():
    hits = [hit(i, d) for i, d in enumerate("aaabbbcdefghij")]
    ctx = select_context(hits)
    assert [c["chunk_id"] for c in ctx] == ["c0", "c1", "c3", "c4", "c6", "c7", "c8", "c9"]
    assert len(ctx) == 8 and max(sum(c["doc_id"] == d for c in ctx) for d in "abcdefgh") == 2


def test_context_returns_fewer_when_candidates_run_out():
    assert len(select_context([hit(0, "a"), hit(1, "a"), hit(2, "a")])) == 2
    assert select_context([]) == []


def test_user_message_numbers_chunks_with_heading_path_and_url():
    msg = build_user_message("why?", [hit(0, "a"), hit(1, "b")])
    assert "[1] a > h0\nURL: https://k8s/a/\ntext 0" in msg and "[2] b > h1\nURL: https://k8s/b/\ntext 1" in msg
    assert msg.endswith("Question: why?")


# -- validation ---------------------------------------------------------------------------------
GOOD = {"answerable": True, "sentences": [{"sentence": "A.", "citations": [1, 3]}, {"sentence": "B.", "citations": [2]}]}
REFUSAL = {"answerable": False, "sentences": [{"sentence": "The provided documentation does not cover this.", "citations": []}]}


def test_valid_answer_and_refusal_pass():
    assert validate_answer(GOOD, 3) == GOOD
    assert validate_answer(REFUSAL, 3) == REFUSAL


@pytest.mark.parametrize("cites", [[0], [4], [-1], [1, 99]])
def test_citation_numbers_outside_1_to_n_are_rejected(cites):
    with pytest.raises(InvalidAnswer, match="outside 1..3"):
        validate_answer({"answerable": True, "sentences": [{"sentence": "A.", "citations": cites}]}, 3)


@pytest.mark.parametrize("bad", [
    {"answerable": True, "sentences": [{"sentence": "A.", "citations": []}]},               # uncited fact
    {"answerable": True, "sentences": [{"sentence": "A.", "citations": ["1"]}]},            # string, not int
    {"answerable": True, "sentences": [{"sentence": "A.", "citations": [True]}]},           # bool is not a citation
    {"answerable": True, "sentences": [{"sentence": "A.", "citations": [1.0]}]},            # float
    {"answerable": True, "sentences": []},                                                  # nothing said
    {"answerable": True, "sentences": [{"sentence": " ", "citations": [1]}]},               # blank
    {"answerable": "yes", "sentences": [{"sentence": "A.", "citations": [1]}]},             # not a bool
    {"answerable": False, "sentences": [{"sentence": "No.", "citations": [1]}]},            # refusal that cites
    {"answerable": False, "sentences": [{"sentence": "No.", "citations": []}, {"sentence": "Also no.", "citations": []}]},
    {"answerable": True},                                                                   # missing key
    [],
])
def test_malformed_answers_are_rejected(bad):
    with pytest.raises(InvalidAnswer):
        validate_answer(bad, 3)


# -- generate(): spend guard, usage-based cost, error handling -----------------------------------------
class Block:
    def __init__(self, text): self.type, self.text = "text", text


class FakeAnthropic:
    def __init__(self, payload, stop_reason="end_turn", usage=(1000, 200)):
        self.calls, self.kwargs = 0, None
        self.payload, self.stop_reason, self.usage = payload, stop_reason, usage
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        self.kwargs = kw
        u = type("U", (), {"input_tokens": self.usage[0], "output_tokens": self.usage[1]})()
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return type("R", (), {"content": [Block(text)], "usage": u, "stop_reason": self.stop_reason})()


CHUNKS = [hit(0, "a"), hit(1, "b"), hit(2, "c")]


def test_cost_comes_from_the_usage_fields(tmp_path):
    client, guard = FakeAnthropic(GOOD, usage=(1_000_000, 100_000)), SpendGuard(50)
    r = generate(client, guard, MODEL, "q", CHUNKS, log_path=str(tmp_path / "log.jsonl"))
    assert r["cost_usd"] == pytest.approx(2.00 + 1.00)  # 1M in at $2 + 100k out at $10
    assert guard.spent == pytest.approx(r["cost_usd"])  # worst-case charge settled to the real cost
    assert json.loads((tmp_path / "log.jsonl").read_text())["usage"] == {"input_tokens": 1_000_000, "output_tokens": 100_000}


def test_request_uses_structured_output_and_no_sampling_or_forced_tool(tmp_path):
    client = FakeAnthropic(GOOD)
    generate(client, SpendGuard(5), MODEL, "q", CHUNKS, log_path=None)
    kw = client.kwargs
    assert kw["output_config"]["format"]["type"] == "json_schema" and kw["output_config"]["effort"] == "medium"
    assert kw["max_tokens"] == MAX_TOKENS and not {"temperature", "top_p", "top_k", "tool_choice", "thinking"} & set(kw)


def test_spend_limit_aborts_before_the_api_call():
    client = FakeAnthropic(GOOD)
    with pytest.raises(BudgetExceeded):
        generate(client, SpendGuard(0.0001), MODEL, "q", CHUNKS, log_path=None)
    assert client.calls == 0


def test_dry_run_and_declined_confirmation_make_no_call():
    client = FakeAnthropic(GOOD)
    r = generate(client, SpendGuard(5), MODEL, "q", CHUNKS, dry_run=True, log_path=None)
    assert client.calls == 0 and r["estimate"]["worst_case_cost"] > r["estimate"]["input_cost_est"] > 0 and "answer" not in r
    with pytest.raises(SystemExit):
        generate(client, SpendGuard(5), MODEL, "q", CHUNKS, confirm=lambda est: False, log_path=None)
    assert client.calls == 0


@pytest.mark.parametrize("payload,stop", [
    ("not json at all", "end_turn"),
    ({"answerable": True, "sentences": [{"sentence": "A.", "citations": [9]}]}, "end_turn"),  # out of range for 3 chunks
    (GOOD, "max_tokens"),
    (GOOD, "refusal"),
])
def test_bad_model_output_is_rejected_but_still_billed_and_logged(tmp_path, payload, stop):
    client, guard, log = FakeAnthropic(payload, stop_reason=stop), SpendGuard(5), tmp_path / "log.jsonl"
    with pytest.raises(InvalidAnswer):
        generate(client, guard, MODEL, "q", CHUNKS, log_path=str(log))
    assert guard.spent == pytest.approx(cost_usd(MODEL, 1000, 200))  # the tokens were spent even though the answer is unusable
    assert "error" in json.loads(log.read_text())


def test_unknown_model_has_no_price():
    assert MODEL in PRICES
    with pytest.raises(ValueError):
        cost_usd("mystery-model", 1, 1)
