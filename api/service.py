"""Request logic for the API: /search and /ask, with the spend ledger in front of every paid call.

Nothing here puts an exception message, a path or an environment value into a response: errors are mapped to fixed codes and messages,
and logs record the exception CLASS only (provider error text can echo parts of a key).
"""
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import elasticsearch
import openai

from api.ledger import BudgetExhausted, Ledger
from ingest.embed_cache import BudgetExceeded
from rag import generate as G
from rag import verify as V
from rag.retrieve import search as retrieve_search

VERDICT_ORDER = {"yes": 2, "partial": 1, "no": 0}


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int, extra: dict | None = None):
        super().__init__(code)
        self.code, self.message, self.status, self.extra = code, message, status, extra or {}


class LedgerGuard:
    """Gives rag.generate / rag.verify / embed_missing the SpendGuard interface (charge / settle / api_tokens) on top of the ledger.
    charge() reserves the full worst case first and raises BudgetExceeded when the ledger refuses; settle() replaces it by the real cost."""

    def __init__(self, ledger: Ledger):
        self.ledger, self.spent, self.api_tokens = ledger, 0.0, 0
        self._open: list[tuple[str, float, str]] = []

    def charge(self, usd: float, what: str = "call") -> None:
        try:
            rid = self.ledger.reserve(usd, what)
        except BudgetExhausted as e:
            raise BudgetExceeded(str(e)) from None
        self._open.append((rid, usd, what))

    def settle(self, charged: float, actual: float) -> None:
        for i in range(len(self._open) - 1, -1, -1):
            rid, usd, _ = self._open[i]
            if abs(usd - charged) < 1e-12:
                self.ledger.settle(rid, actual)
                self.spent += actual
                del self._open[i]
                return

    def finish(self, failed: bool) -> None:
        """Close what is still open. Embedding batches (which have no separate settle call) count at their estimate; a generation or
        verification call that never produced a response (so no usage is known) is released when the request failed."""
        for rid, usd, what in self._open:
            if what.startswith("batch") or not failed:
                self.ledger.settle(rid, usd)
                self.spent += usd
            else:
                self.ledger.release(rid)
        self._open = []


@dataclass
class Services:
    es: object
    index: str
    ledger: Ledger
    make_embedder: Callable  # guard -> embedder (callable, with is_cached / estimate), serving cache only
    client_factory: Callable  # () -> anthropic client (created on first paid use)
    answer_model: str
    verifier_model: str
    log_dir: Path
    _client: object = field(default=None, repr=False)

    def client(self):
        if self._client is None:
            self._client = self.client_factory()
        return self._client


def _log(svc: Services, rec: dict) -> None:
    svc.log_dir.mkdir(parents=True, exist_ok=True)
    with open(svc.log_dir / "requests.jsonl", "a", encoding="utf8") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **rec}, ensure_ascii=False) + "\n")


def _classify(e: Exception) -> ApiError:
    """Map any internal failure to a fixed, safe error. Only the class name goes to the log, never the message."""
    if isinstance(e, ApiError):
        return e
    if isinstance(e, BudgetExceeded):
        return ApiError("budget_exhausted", "The spend limit for this service would be exceeded; no paid call was made.", 429)
    if isinstance(e, openai.OpenAIError):
        return ApiError("embedding_unavailable", "The embedding service failed.", 502)
    if isinstance(e, elasticsearch.ApiError | elasticsearch.TransportError | ConnectionError):
        return ApiError("search_unavailable", "The search backend is unavailable.", 503)
    if isinstance(e, G.InvalidAnswer):
        return ApiError("invalid_model_output", "The model returned an answer that failed validation; it was discarded.", 502)
    return ApiError("internal_error", "Internal error.", 500)


def _hit(rank: int, h: dict) -> dict:
    out = {"rank": rank, "score": h["score"], "chunk_id": h["chunk_id"], "doc_id": h["doc_id"], "url": h["url"], "title": h.get("title"),
           "heading_path": h["heading_path"], "token_count": h.get("token_count"), "content": h["content"]}
    if "ranks" in h:
        out["ranks"] = h["ranks"]
    return out


def do_search(svc: Services, query: str, mode: str, chunker: str, k: int) -> dict:
    t0, guard, failed = time.perf_counter(), LedgerGuard(svc.ledger), True
    hits, cache_hit = [], True
    try:
        embed = svc.make_embedder(guard) if mode != "bm25" else None
        if embed is not None:
            cache_hit = embed.is_cached(query)
        hits = retrieve_search(svc.es, svc.index, query, mode, chunker, k, embed=embed)
        failed = False
    except Exception as e:
        err = _classify(e)
        guard.finish(True)
        _log(svc, {"endpoint": "search", "status": f"error:{err.code}", "error_class": type(e).__name__, "mode": mode, "chunker": chunker, "k": k, "cost_usd": round(guard.spent, 8)})
        raise err from None
    finally:
        guard.finish(failed)
    out = {"query": query, "mode": mode, "chunker": chunker, "k": k, "results": [_hit(i, h) for i, h in enumerate(hits, 1)],
           "query_embedding": None if mode == "bm25" else {"cache_hit": cache_hit}, "cost_usd": round(guard.spent, 8),
           "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
    _log(svc, {"endpoint": "search", "status": "ok", "mode": mode, "chunker": chunker, "k": k, "results": len(hits), "cost_usd": out["cost_usd"], "latency_ms": out["latency_ms"]})
    return out


def _best_verdicts(judgements: list[dict]) -> dict[int, dict]:
    best: dict[int, dict] = {}
    for j in judgements:
        if j["sentence"] not in best or VERDICT_ORDER[j["verdict"]] > VERDICT_ORDER[best[j["sentence"]]["verdict"]]:
            best[j["sentence"]] = j
    return best


def do_ask(svc: Services, query: str) -> dict:
    t_start, guard = time.perf_counter(), LedgerGuard(svc.ledger)
    floor = G.estimate(G.SYSTEM, "", svc.answer_model)["worst_case_cost"]  # the least an answer call can reserve (empty context + the output ceiling)
    if not svc.ledger.can_afford(floor):  # refuse before ANY paid call, including the query embedding
        _log(svc, {"endpoint": "ask", "status": "error:budget_exhausted", "cost_usd": 0.0})
        raise ApiError("budget_exhausted", "The spend limit for this service would be exceeded; no paid call was made.", 429)
    lat, usage, costs = {}, {"answer": None, "verifier": None}, {"answer": 0.0, "verifier": 0.0}
    failed = True
    try:
        t = time.perf_counter()
        chunks = G.retrieve_context(svc.es, svc.index, svc.make_embedder(guard), query)
        lat["retrieval"] = round((time.perf_counter() - t) * 1000, 1)
        gen_log = str(svc.log_dir / "generation_log.jsonl")
        t = time.perf_counter()
        try:
            res = G.generate(svc.client(), guard, svc.answer_model, query, chunks, confirm=None, dry_run=False, log_path=gen_log, extra={"endpoint": "ask"})
        except G.InvalidAnswer as e:
            guard.finish(False)  # the call returned and was billed (generate() settled it and logged the tokens)
            err = ApiError("invalid_model_output", "The model returned an answer that failed validation; it was discarded.", 502, {"cost_usd": round(guard.spent, 8)})
            _log(svc, {"endpoint": "ask", "status": "error:invalid_model_output", "error_class": "InvalidAnswer", "cost_usd": round(guard.spent, 8), "generation_log": "generation_log.jsonl"})
            raise err from None
        lat["generation"] = round((time.perf_counter() - t) * 1000, 1)
        usage["answer"], costs["answer"] = res["usage"], res["cost_usd"]
        answer = res["answer"]
        verification = {"status": "not_applicable", "citation_precision": None, "pairs": [], "unsupported_sentences": [], "partially_supported_sentences": []}
        verdicts: dict[int, dict] = {}
        flag = False
        if answer["answerable"]:
            t = time.perf_counter()
            try:
                v = V.verify_answer(svc.client(), guard, svc.verifier_model, answer["sentences"], {c["n"]: c["content"] for c in res["chunks"]})
                usage["verifier"], costs["verifier"] = v["usage"], v["cost_usd"]
                verdicts = _best_verdicts(v["judgements"])
                s = v["summary"]
                verification = {"status": "ok", "citation_precision": s["citation_precision"], "unsupported_sentences": s["unsupported_sentences"],
                                "partially_supported_sentences": s["partially_supported_sentences"],
                                "pairs": [{"sentence": j["sentence"], "citation": j["citation"], "verdict": j["verdict"], "reason": j["reason"]} for j in v["judgements"]]}
                flag = bool(s["unsupported_sentences"])
            except V.InvalidVerdicts as e:
                if e.usage:
                    usage["verifier"], costs["verifier"] = e.usage, e.cost_usd
                verification = {"status": "failed", "reason": "The verifier returned unusable output.", "citation_precision": None, "pairs": [], "unsupported_sentences": [], "partially_supported_sentences": []}
                flag = None
                _log(svc, {"endpoint": "ask", "status": "verification_failed", "error_class": "InvalidVerdicts", "usage": e.usage, "cost_usd": e.cost_usd})
            except BudgetExceeded:
                verification = {"status": "skipped", "reason": "Not enough spend budget left to verify; the answer is unverified.", "citation_precision": None, "pairs": [], "unsupported_sentences": [], "partially_supported_sentences": []}
                flag = None
            lat["verification"] = round((time.perf_counter() - t) * 1000, 1)
        failed = False
        guard.finish(False)
        cited = sorted({c for s in answer["sentences"] for c in s["citations"]})
        by_n = {c["n"]: c for c in res["chunks"]}
        total_cost = round(guard.spent, 8)
        lat["total"] = round((time.perf_counter() - t_start) * 1000, 1)
        out = {"query": query, "answerable": answer["answerable"],
               "sentences": [{"n": i, "sentence": s["sentence"], "citations": s["citations"],
                              "verdict": verdicts[i]["verdict"] if i in verdicts else None} for i, s in enumerate(answer["sentences"], 1)],
               "citations": [{"n": n, "chunk_id": by_n[n]["chunk_id"], "doc_id": by_n[n]["doc_id"], "url": by_n[n]["url"], "heading_path": by_n[n]["heading_path"], "content": by_n[n]["content"]} for n in cited],
               "verification": verification, "unsupported_sentence_flag": flag, "latency_ms": lat, "usage": usage,
               "cost_usd": {"answer": round(costs["answer"], 8), "verifier": round(costs["verifier"], 8), "total_including_embedding": total_cost}}
        _log(svc, {"endpoint": "ask", "status": "ok", "answerable": answer["answerable"], "verification": verification["status"], "usage": usage, "cost_usd": total_cost, "latency_ms": lat["total"]})
        return out
    except ApiError:
        raise
    except Exception as e:
        err = _classify(e)
        guard.finish(True)
        _log(svc, {"endpoint": "ask", "status": f"error:{err.code}", "error_class": type(e).__name__, "cost_usd": round(guard.spent, 8)})
        raise err from None
    finally:
        guard.finish(failed)
