import json
import random

import pytest

from eval import draft_questions as dq
from eval.overlap import doc_frequency
from ingest.embed_cache import BudgetExceeded, SpendGuard

MODEL = "claude-sonnet-5-5"


def chunk(i, folder="concepts", tok=300, content=None, doc=None):
    return {"chunk_id": f"c{i:04d}", "doc_id": doc or f"{folder}/area/page{i}", "url": f"https://kubernetes.io/docs/{folder}/area/page{i}/",
            "title": f"Page {i}", "heading_path": f"Page {i} > Section", "token_count": tok,
            "content": content if content is not None else f"The `maxSurge` field and the `--grace-period` flag matter. Plain prose number {i} about scheduling."}


def pool(n_per_folder=40):
    return [chunk(1000 * k + i, f) for k, f in enumerate(("concepts", "tasks", "reference")) for i in range(n_per_folder)]


# -- eligibility ------------------------------------------------------------------------------------
def test_identifiers_find_flags_camelcase_snake_and_hyphenated_terms():
    c = "Use `--max-pods`, the `maxUnavailable` field, `kube-proxy`, `pod_name`, and `plain` or `x`."
    assert dq.identifiers(c) == ["--max-pods", "maxUnavailable", "kube-proxy", "pod_name"]


def test_eligibility_filters_size_code_tables_and_identifier_need():
    assert dq.eligible(chunk(1), need_identifier=False) and dq.eligible(chunk(1), need_identifier=True)
    assert not dq.eligible(chunk(2, tok=100), False) and not dq.eligible(chunk(3, tok=900), False)
    assert not dq.eligible(chunk(4, content="```yaml\n" + "a: b\n" * 50 + "```\nshort"), False)  # mostly code
    assert not dq.eligible(chunk(5, content="\n".join("| a | b | c |" for _ in range(30)) + "\ntext"), False)  # mostly table
    assert dq.eligible(chunk(6, content="No identifiers here, just words."), False)
    assert not dq.eligible(chunk(6, content="No identifiers here, just words."), True)
    assert not dq.eligible(chunk(7, folder="blog"), False)


# -- sampling -----------------------------------------------------------------------------------------
def test_sample_respects_quota_spreads_folders_and_uses_one_chunk_per_page():
    chunks = pool() + [chunk(9000, "concepts", doc="concepts/area/page1")]  # a second chunk of an existing page
    got = dq.sample_chunks(chunks, dq.QUOTAS["conceptual"], False, set(), random.Random(1))
    by = {f: sum(1 for c in got if dq.top_folder(c["doc_id"]) == f) for f in dq.QUOTAS["conceptual"]}
    assert by == dq.QUOTAS["conceptual"] and len({c["doc_id"] for c in got}) == len(got)


def test_chunks_with_html_entities_are_never_sampled():
    assert not dq.eligible(chunk(1, content='Set the value to &quot;json&quot; for `maxSurge`.'), False)
    assert not dq.eligible(chunk(2, content="Plain text but `maxSurge`.") | {"heading_path": "A &#34;b&#34;"}, False)
    assert dq.eligible(chunk(3, content="Plain text with `maxSurge` and a < b."), True)


def test_generated_listings_are_excluded_from_conceptual_but_not_from_mixed_sampling():
    cfg = [chunk(i, "reference", doc=f"reference/config-api/cfg{i}") for i in range(30)]
    other = [chunk(100 + i, "reference", doc=f"reference/using-api/page{i}") for i in range(30)]
    todo = dq.plan(cfg + other)
    conceptual = [c["doc_id"] for t, c in todo if t == "conceptual"]
    mixed = [c["doc_id"] for t, c in todo if t == "mixed"]
    assert conceptual and not any(d.startswith(dq.CONCEPTUAL_EXCLUDE) for d in conceptual)
    assert any(d.startswith("reference/config-api/") for d in mixed + [c["doc_id"] for c in cfg]) and len(conceptual) == dq.QUOTAS["conceptual"]["reference"]


def test_sample_is_deterministic_and_independent_of_input_order():
    a = dq.sample_chunks(pool(), dq.QUOTAS["mixed"], True, set(), random.Random(7))
    b = dq.sample_chunks(list(reversed(pool())), dq.QUOTAS["mixed"], True, set(), random.Random(7))
    assert [c["chunk_id"] for c in a] == [c["chunk_id"] for c in b]


def test_plan_gives_22_conceptual_and_16_mixed_on_disjoint_pages():
    todo = dq.plan(pool())
    types = [t for t, _ in todo]
    assert types.count("conceptual") == 22 and types.count("mixed") == 16
    docs = [c["doc_id"] for _, c in todo]
    assert len(set(docs)) == len(docs)  # no page used twice across the two types


def test_plan_warns_when_too_few_chunks_are_eligible(capsys):
    todo = dq.plan(pool(3))
    assert len(todo) < 38 and "WARNING" in capsys.readouterr().out


# -- validation ------------------------------------------------------------------------------------------
PASSAGE = "The `maxSurge` field says how many Pods can be created above the desired count during an update."


def ok(**kw):
    return {"question": "How many extra copies may be started while an update rolls out?", "reference_answer": "Up to the maxSurge value.", "exact_term": "", **kw}


def test_valid_conceptual_and_mixed_drafts():
    assert dq.validate_draft(ok(), "conceptual", PASSAGE)["exact_term"] == ""
    m = ok(question="What does `maxSurge` allow during a rolling update, in plain terms?", exact_term="`maxSurge`")
    assert dq.validate_draft(m, "mixed", PASSAGE)["exact_term"] == "`maxSurge`"


@pytest.mark.parametrize("typ,bad", [
    ("conceptual", ok(exact_term="maxSurge")),                                        # conceptual must not declare an exact term
    ("conceptual", ok(question="Too short")),
    ("conceptual", ok(reference_answer=" ")),
    ("conceptual", {"question": "x " * 10, "reference_answer": "a"}),                  # missing key
    ("mixed", ok()),                                                                   # no exact_term
    ("mixed", ok(exact_term="`maxUnavailable`", question="What is `maxUnavailable` for in a rollout?")),  # not in the passage
    ("mixed", ok(exact_term="`maxSurge`")),                                            # in the passage but not in the question
    ("conceptual", "not a dict"),
])
def test_bad_drafts_are_rejected(typ, bad):
    with pytest.raises(dq.InvalidDraft):
        dq.validate_draft(bad, typ, PASSAGE)


# -- flags ---------------------------------------------------------------------------------------------------
PAGE = "Process ID limits. A single Pod will not be able to bring the whole machine down. Reserve PIDs for the kubelet and daemons."
DF = doc_frequency([PAGE] + ["generic text about scheduling and nodes"] * 20)


def test_a_question_that_reuses_the_pages_words_is_flagged_and_a_paraphrase_is_not():
    copied = {"question": "How can one Pod bring the whole machine down", "exact_term": ""}
    m = dq.draft_metrics(copied, "conceptual", PAGE, DF, 21)
    f = dq.flags_for(m, "conceptual")
    assert m["overlap_ratio"] > 0.5 and any(x.startswith("copied_phrase") for x in f) and any(x.startswith("high_overlap") for x in f)
    para = {"question": "What stops a single workload from starving the host of resources?", "exact_term": ""}
    assert dq.flags_for(dq.draft_metrics(para, "conceptual", PAGE, DF, 21), "conceptual") == []


def test_mixed_draft_does_not_count_its_declared_exact_term_against_itself():
    page = "Set `--eviction-hard` to control when the kubelet starts evicting pods under memory pressure."
    d = {"question": "What does --eviction-hard do when memory is short?", "exact_term": "--eviction-hard"}
    m = dq.draft_metrics(d, "mixed", page, doc_frequency([page] + ["other text"] * 20), 21)
    from eval.overlap import content_terms
    assert not set(m["distinctive_shared"]) & content_terms("--eviction-hard")  # the exact term's own words are never counted
    assert m["copied_phrases"] == []  # and the term is not reported as a copied phrase either


# -- drafting with a fake client -----------------------------------------------------------------------------
class Block:
    def __init__(self, t): self.type, self.text = "text", t


class FakeClient:
    def __init__(self, payload, stop="end_turn", usage=(900, 150)):
        self.calls, self.payload, self.stop, self.usage = 0, payload, stop, usage
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        u = type("U", (), {"input_tokens": self.usage[0], "output_tokens": self.usage[1]})()
        txt = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return type("R", (), {"content": [Block(txt)], "usage": u, "stop_reason": self.stop})()


def test_draft_one_returns_record_with_cost_from_usage_and_flags():
    c = chunk(1, content=PASSAGE)
    g = SpendGuard(5)
    r = dq.draft_one(FakeClient(ok()), g, MODEL, "conceptual", c, DF, 21, PAGE)
    assert r["source_doc_id"] == c["doc_id"] and r["question"] and "flags" in r and "metrics" in r
    assert r["cost_usd"] == pytest.approx(900 / 1e6 * 2 + 150 / 1e6 * 10) and g.spent == pytest.approx(r["cost_usd"])


@pytest.mark.parametrize("payload,stop", [("not json", "end_turn"), (ok(exact_term="x"), "end_turn"), (ok(), "max_tokens")])
def test_invalid_model_output_becomes_an_error_record_but_is_still_billed(payload, stop):
    g = SpendGuard(5)
    r = dq.draft_one(FakeClient(payload, stop=stop), g, MODEL, "conceptual", chunk(1, content=PASSAGE), DF, 21, PAGE)
    assert "error" in r and "question" not in r and g.spent > 0


def test_spend_guard_stops_drafting_before_the_call():
    c = FakeClient(ok())
    with pytest.raises(BudgetExceeded):
        dq.draft_one(c, SpendGuard(1e-9), MODEL, "conceptual", chunk(1, content=PASSAGE), DF, 21, PAGE)
    assert c.calls == 0


def test_review_table_marks_flagged_and_failed_drafts():
    md = dq.render_md([
        {"id": "d001", "type": "conceptual", "question": "Q?", "reference_answer": "A.", "exact_term": "", "source_doc_id": "concepts/x", "source_url": "u",
         "source_heading_path": "X", "metrics": {"overlap_ratio": 0.7, "distinctive_shared": ["a", "b"], "copied_phrases": []}, "flags": ["high_overlap(0.7)"]},
        {"id": "d002", "type": "mixed", "error": "exact_term not in passage", "source_doc_id": "tasks/y"},
    ])
    assert "d001 · conceptual  **FLAGGED**" in md and "DRAFT FAILED: exact_term not in passage" in md and "suggestion" in md


def test_dry_run_prints_sample_and_estimate_and_never_calls_the_api(tmp_path, monkeypatch, capsys):
    p = tmp_path / "heading.jsonl"
    p.write_text("\n".join(json.dumps(c) for c in pool()), encoding="utf8")
    monkeypatch.setenv("ANSWER_MODEL", MODEL)
    import builtins
    monkeypatch.setattr(builtins, "input", lambda *a: pytest.fail("a dry run must not prompt"))
    dq.main(["--dry-run", "--chunks", str(p)])
    out = capsys.readouterr().out
    assert "38 drafts" in out and "typical cost $" in out and "worst case $" in out and "dry run: no API call made" in out
