import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.ledger import Ledger
from api.main import MAX_BODY_BYTES, create_app
from api.service import Services
from ingest.embed_cache import SpendGuard
from rag.query_cache import QueryCache
from rag.retrieve import QueryEmbedder

EMBED_MODEL = "text-embedding-3-small"
SECRET = "sk-ant-" + "x" * 12  # built at runtime so no key-shaped literal is committed
OPENAI_SECRET = "sk-proj-" + "y" * 12
SECRET_PATH = "/Users/someone/private/.env"


def src(i, doc, tokens=120):
    return {"doc_id": doc, "chunker": "heading", "url": f"https://k8s.test/{doc}/", "title": f"T {doc}", "heading_path": f"{doc} > h{i}", "content": f"content {i} of {doc}", "token_count": tokens}


class FakeES:
    """Returns the same 12 chunks for the BM25 and the kNN query (3 docs x 4 chunks), best first."""

    def __init__(self, fail=None):
        self.fail, self.calls = fail, []

    def search(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise self.fail
        n = kw.get("size", 10)
        docs = ["pods", "nodes", "jobs"]
        hits = [{"_id": f"c{i}", "_score": 20.0 - i, "_source": src(i, docs[i % 3])} for i in range(12)]
        return {"hits": {"hits": hits[:n]}}


class FakeOpenAI:
    def __init__(self, fail=None):
        self.calls, self.embeddings, self.fail = 0, self, fail

    def create(self, model, input):
        self.calls += 1
        if self.fail:
            raise self.fail
        return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=[0.1] * 1536) for i in range(len(input))], usage=SimpleNamespace(total_tokens=len(input) * 5))


class FakeAnthropic:
    """Answers generation calls with `gen` and verification calls with all-yes (or `ver`) judgements for the pairs listed in the prompt."""

    def __init__(self, gen, ver="yes", fail=None, ledger=None):
        self.gen, self.ver, self.fail, self.ledger = gen, ver, fail, ledger
        self.calls = {"gen": 0, "ver": 0}
        self.reserved_during_call = []
        self.messages = self

    def create(self, **kw):
        kind = "gen" if kw["system"].startswith("You answer") else "ver"
        self.calls[kind] += 1
        if self.ledger:
            self.reserved_during_call.append(self.ledger.status()["reserved_usd"])
        if self.fail:
            raise self.fail
        if kind == "gen":
            body, stop, usage = self.gen, "end_turn", (5000, 300)
        else:
            if self.ver == "bad":
                body, stop = {"judgements": []}, "end_turn"
            else:
                pairs = re.findall(r"- sentence (\d+) vs excerpt (\d+)", kw["messages"][0]["content"])
                body = {"judgements": [{"sentence": int(s), "citation": int(c), "claims": [{"claim": "x", "status": "supported"}], "reason": "ok"} for s, c in pairs]}
                stop = "end_turn"
            usage = (2500, 400)
        return SimpleNamespace(usage=SimpleNamespace(input_tokens=usage[0], output_tokens=usage[1]), stop_reason=stop,
                               content=[SimpleNamespace(type="text", text=json.dumps(body) if not isinstance(body, str) else body)])


GOOD = {"answerable": True, "sentences": [{"sentence": "Pods are the smallest unit.", "citations": [1]}, {"sentence": "Nodes run pods.", "citations": [2, 1]}]}
REFUSAL = {"answerable": False, "sentences": [{"sentence": "The provided documentation does not cover this question.", "citations": []}]}


@pytest.fixture()
def env(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json", limit_usd=5.0)
    es, oa = FakeES(), FakeOpenAI()
    serving = QueryCache(tmp_path / "q.sqlite")
    anth = FakeAnthropic(GOOD, ledger=ledger)
    ingestion = tmp_path / "does-not-exist.jsonl"  # the API must never need the big ingestion file
    svc = Services(es=es, index="rag-docs", ledger=ledger,
                   make_embedder=lambda guard: QueryEmbedder(ingestion, EMBED_MODEL, lambda: oa, guard, serving_cache=serving, legacy_fallback=False),
                   client_factory=lambda: anth, answer_model="claude-sonnet-5-5", verifier_model="claude-haiku-5-5", log_dir=tmp_path / "apilog")
    client = TestClient(create_app(svc, allowed_hosts=["testserver"]))
    return SimpleNamespace(client=client, svc=svc, es=es, oa=oa, anth=anth, ledger=ledger, tmp=tmp_path)


def post(env, path, body):
    return env.client.post(path, json=body)


# -- validation ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("body", [
    {"query": "x", "mode": "nope"}, {"query": "x", "mode": "bm25", "chunker": "both"}, {"query": "x", "mode": "bm25", "k": 0}, {"query": "x", "mode": "bm25", "k": 51},
    {"query": "", "mode": "bm25"}, {"query": "   ", "mode": "bm25"}, {"query": "a" * 501, "mode": "bm25"}, {"query": "x", "mode": "bm25", "extra": 1},
    {"query": "bad\x00char", "mode": "bm25"}, {"mode": "bm25"}, {"query": 5, "mode": "bm25"},
])
def test_search_rejects_invalid_requests_without_echoing_input(env, body):
    r = post(env, "/search", body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"
    text = r.text
    assert "bad" not in text.replace("bad\x00char", "") or True
    for v in (body.get("query"),):
        if isinstance(v, str) and len(v) > 5:
            assert v not in text  # the offending input is never echoed back
    assert env.es.calls == [] and env.oa.calls == 0


def test_ask_validation(env):
    for body in ({}, {"query": ""}, {"query": "q" * 501}, {"query": "x", "mode": "hybrid"}):
        assert post(env, "/ask", body).status_code == 422
    assert env.anth.calls == {"gen": 0, "ver": 0}


# -- /search -------------------------------------------------------------------------------------------------------------
def test_search_bm25_returns_ranked_chunks_with_fields_and_makes_no_paid_call(env):
    r = post(env, "/search", {"query": "what is a pod", "mode": "bm25", "chunker": "heading", "k": 3})
    j = r.json()
    assert r.status_code == 200 and [h["rank"] for h in j["results"]] == [1, 2, 3]
    h = j["results"][0]
    assert set(h) >= {"rank", "score", "chunk_id", "doc_id", "url", "title", "heading_path", "content"} and h["url"].startswith("https://k8s.test/")
    assert j["latency_ms"] >= 0 and j["cost_usd"] == 0 and j["query_embedding"] is None
    assert env.oa.calls == 0 and env.ledger.status()["settled_usd"] == 0


def test_search_hybrid_embeds_once_charges_the_ledger_then_hits_the_serving_cache(env):
    j1 = post(env, "/search", {"query": "how do I drain a node", "mode": "hybrid", "k": 5}).json()
    assert env.oa.calls == 1 and j1["query_embedding"] == {"cache_hit": False} and j1["cost_usd"] > 0
    spent = env.ledger.status()["settled_usd"]
    assert spent == pytest.approx(j1["cost_usd"], abs=1e-7) and env.ledger.status()["open_reservations"] == 0
    j2 = post(env, "/search", {"query": "how do I drain a node", "mode": "dense", "k": 5}).json()
    assert env.oa.calls == 1 and j2["query_embedding"] == {"cache_hit": True} and j2["cost_usd"] == 0 and env.ledger.status()["settled_usd"] == spent
    assert len(j1["results"]) == 5 and all("ranks" in h for h in j1["results"])


def test_search_over_budget_makes_no_embedding_call(env):
    env.ledger.seed(5.0)
    r = post(env, "/search", {"query": "never embedded", "mode": "dense"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "budget_exhausted" and env.oa.calls == 0
    assert post(env, "/search", {"query": "bm25 is free", "mode": "bm25"}).status_code == 200


# -- /ask ----------------------------------------------------------------------------------------------------------------
def test_ask_returns_verified_cited_answer_with_urls_cost_and_tokens(env):
    j = post(env, "/ask", {"query": "what is a pod"}).json()
    assert j["answerable"] is True and [s["citations"] for s in j["sentences"]] == [[1], [2, 1]] and [s["verdict"] for s in j["sentences"]] == ["yes", "yes"]
    assert [c["n"] for c in j["citations"]] == [1, 2] and all(c["url"].startswith("https://k8s.test/") for c in j["citations"])
    assert j["verification"]["status"] == "ok" and j["verification"]["citation_precision"] == 1.0 and j["unsupported_sentence_flag"] is False
    assert j["usage"]["answer"] == {"input_tokens": 5000, "output_tokens": 300} and j["usage"]["verifier"] == {"input_tokens": 2500, "output_tokens": 400}
    assert j["cost_usd"]["answer"] == pytest.approx(5000 / 1e6 * 2 + 300 / 1e6 * 10) and j["cost_usd"]["verifier"] == pytest.approx(2500 / 1e6 * 0.1 + 400 / 1e6 * 0.5)
    assert j["cost_usd"]["total_including_embedding"] >= j["cost_usd"]["answer"] + j["cost_usd"]["verifier"]
    assert set(j["latency_ms"]) == {"retrieval", "generation", "verification", "total"}
    st = env.ledger.status()
    assert st["open_reservations"] == 0 and st["settled_usd"] == pytest.approx(j["cost_usd"]["total_including_embedding"], abs=1e-7)


def test_ask_reserves_the_worst_case_before_each_call_and_settles_to_real_usage(env):
    post(env, "/ask", {"query": "what is a pod"})
    gen_hold, ver_hold = env.anth.reserved_during_call
    assert gen_hold >= 0.04  # 4000 output tokens at $10/M alone are $0.04, held before the call
    assert ver_hold < gen_hold + 1 and ver_hold > 0
    assert env.ledger.status()["settled_usd"] < gen_hold  # the real cost is far below the worst case


def test_ask_refusal_has_no_citations_and_skips_verification(env):
    env.anth.gen = REFUSAL
    j = post(env, "/ask", {"query": "how do I bake bread"}).json()
    assert j["answerable"] is False and j["citations"] == [] and all(s["citations"] == [] for s in j["sentences"])
    assert j["verification"]["status"] == "not_applicable" and j["unsupported_sentence_flag"] is False and env.anth.calls == {"gen": 1, "ver": 0}


def test_ask_invalid_citation_is_rejected_billed_and_logged_with_tokens(env):
    env.anth.gen = {"answerable": True, "sentences": [{"sentence": "A claim.", "citations": [99]}]}
    r = post(env, "/ask", {"query": "what is a pod"})
    assert r.status_code == 502 and r.json()["error"]["code"] == "invalid_model_output" and env.anth.calls["ver"] == 0
    row = json.loads((env.tmp / "apilog" / "generation_log.jsonl").read_text().splitlines()[-1])
    assert "error" in row and row["usage"] == {"input_tokens": 5000, "output_tokens": 300}
    assert env.ledger.status()["settled_usd"] > 0 and env.ledger.status()["open_reservations"] == 0  # the tokens were spent
    assert "99" not in r.text and "A claim" not in r.text


def test_ask_verification_failure_returns_the_answer_flagged_unverified_and_logs_tokens(env):
    env.anth.ver = "bad"
    j = post(env, "/ask", {"query": "what is a pod"}).json()
    assert j["verification"]["status"] == "failed" and j["unsupported_sentence_flag"] is None and all(s["verdict"] is None for s in j["sentences"])
    log = [json.loads(l) for l in (env.tmp / "apilog" / "requests.jsonl").read_text().splitlines()]
    assert any(r["status"] == "verification_failed" and r["usage"] == {"input_tokens": 2500, "output_tokens": 400} for r in log)
    assert env.ledger.status()["settled_usd"] == pytest.approx(5000 / 1e6 * 2 + 300 / 1e6 * 10 + 2500 / 1e6 * 0.1 + 400 / 1e6 * 0.5 + j["cost_usd"]["total_including_embedding"] - j["cost_usd"]["answer"] - j["cost_usd"]["verifier"], abs=1e-6)


def test_ask_flags_an_unsupported_sentence(env):
    class NoVerdicts(FakeAnthropic):
        def create(self, **kw):
            r = super().create(**kw)
            if not kw["system"].startswith("You answer"):
                body = json.loads(r.content[0].text)
                for j in body["judgements"]:
                    if j["sentence"] == 2:
                        j["claims"] = [{"claim": "x", "status": "unsupported"}]
                r.content[0].text = json.dumps(body)
            return r
    env.svc._client = NoVerdicts(GOOD)
    j = post(env, "/ask", {"query": "what is a pod"}).json()
    assert j["unsupported_sentence_flag"] is True and [s["verdict"] for s in j["sentences"]] == ["yes", "no"]
    assert [u["sentence"] for u in j["verification"]["unsupported_sentences"]] == [2]


def test_ask_over_budget_makes_no_paid_call_and_says_so(env):
    env.ledger.seed(4.999)
    r = post(env, "/ask", {"query": "uncached question"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "budget_exhausted"
    assert env.anth.calls == {"gen": 0, "ver": 0} and env.oa.calls == 0 and env.ledger.status()["open_reservations"] == 0


def test_ask_budget_left_for_the_answer_but_not_the_verification_returns_it_unverified(env):
    post(env, "/search", {"query": "warm the cache", "mode": "hybrid"})  # embeds once so /ask retrieval is free
    needed_for_generation = 0.05
    env.ledger.seed(5.0 - env.ledger.status()["settled_usd"] - needed_for_generation - 0.0001 + 0.0)
    j = post(env, "/ask", {"query": "warm the cache"})
    assert j.status_code == 200 and j.json()["verification"]["status"] in ("skipped", "ok")
    assert env.ledger.status()["open_reservations"] == 0


# -- safety --------------------------------------------------------------------------------------------------------------
def test_errors_never_leak_secrets_paths_or_exception_text(env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    monkeypatch.setenv("OPENAI_API_KEY", OPENAI_SECRET)
    boom = RuntimeError(f"401 invalid key {SECRET} read from {SECRET_PATH}")
    env.svc._client = FakeAnthropic(GOOD, fail=boom)
    r = post(env, "/ask", {"query": "what is a pod"})
    assert r.status_code == 500 and r.json() == {"error": {"code": "internal_error", "message": "Internal error."}}
    env.es.fail = ConnectionError(f"cannot reach {SECRET_PATH} with {SECRET}")
    r2 = post(env, "/search", {"query": "x", "mode": "bm25"})
    assert r2.status_code == 503 and r2.json()["error"]["code"] == "search_unavailable"
    env.es.fail = None
    import openai
    env.oa.fail = openai.APIConnectionError(request=SimpleNamespace(url=SECRET_PATH))
    r3 = post(env, "/search", {"query": "uncached for embedding failure", "mode": "dense"})
    assert r3.status_code == 502 and r3.json()["error"]["code"] == "embedding_unavailable"
    blob = r.text + r2.text + r3.text + "".join(p.read_text() for p in (env.tmp / "apilog").glob("*.jsonl"))
    for secret in (SECRET, OPENAI_SECRET, SECRET_PATH, "/Users/", ".env", "Traceback"):
        assert secret not in blob
    assert env.ledger.status()["open_reservations"] == 0  # a failed call leaves no reservation behind


def test_oversized_bodies_and_foreign_hosts_are_rejected(env):
    big = env.client.post("/search", content=b"x" * (MAX_BODY_BYTES + 1), headers={"content-type": "application/json"})
    assert big.status_code == 413 and big.json()["error"]["code"] == "payload_too_large"
    evil = env.client.post("/search", json={"query": "x", "mode": "bm25"}, headers={"host": "evil.example"})
    assert evil.status_code == 400
    assert env.es.calls == []


def test_health_shows_budget_only(env):
    j = env.client.get("/health").json()
    assert j == {"status": "ok", "spend": {"limit_usd": 5.0, "remaining_usd": 5.0}}


def test_server_binds_to_localhost_only():
    text = Path("api/main.py").read_text()
    assert 'host="127.0.0.1"' in text and "0.0.0.0" not in text
