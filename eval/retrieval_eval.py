"""Baseline retrieval eval: bm25 / dense / hybrid (Python RRF) x fixed / heading on the frozen golden set.

    python -m eval.retrieval_eval --dry-run        # query-embedding cost estimate, no API call, no ES search
    python -m eval.retrieval_eval --yes            # run (after the owner approved the estimate)

Scores the answerable golden questions at doc level (chunk lists collapsed to distinct docs): Recall@5, Recall@10 (share
of expected docs in the top k distinct docs) and MRR (rank of the first expected doc). Unanswerable questions are
excluded. Exhausted lists stay in the denominator as misses (eval/metrics.py); their count is reported separately.
Baseline only: current settings, no tuning, no native RRF, no pool sweep.
"""
import argparse
import hashlib
import json
import os
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from eval.metrics import KS, aggregate, evaluate_query
from rag.retrieve import BM25_FIELDS, NUM_CANDIDATES, POOL, RRF_K, QueryEmbedder, bm25, dense, distinct_docs, hybrid, knn_clause
from ingest.embed_cache import SpendGuard

CHUNKERS = ("fixed", "heading")
MODES = ("bm25", "dense", "hybrid")
TYPES = ("exact_term", "mixed", "conceptual")
TINY = 100  # tokens: a chunk under this counts as tiny (token_count is measured on the embedded text)
TOP_CHUNKS = 5
BOOTSTRAP_N, BOOTSTRAP_SEED = 10000, 0
HYBRID_TOP = 2 * POOL  # the full fused list (both inner lists are POOL long), so Recall@10 over distinct docs is never cut by the fusion


# -- pure helpers (unit-tested) ---------------------------------------------------------------
def doc_ranks(hits: list[dict], expected: list[str]) -> dict[str, int | None]:
    """Rank (1-based, among distinct docs) of every expected doc; None when it is not in the list."""
    ranked = [h["doc_id"] for h in distinct_docs(hits)]
    return {d: (ranked.index(d) + 1 if d in ranked else None) for d in expected}


def first_rank(ranks: dict[str, int | None]) -> int | None:
    found = [r for r in ranks.values() if r is not None]
    return min(found) if found else None


def compare_ranks(a: int | None, b: int | None) -> str:
    """'win' if a ranks the first expected doc better (smaller rank) than b, 'loss' if worse, else 'tie' (a missing rank is worst)."""
    ka, kb = (a if a is not None else float("inf")), (b if b is not None else float("inf"))
    return "win" if ka < kb else "loss" if ka > kb else "tie"


def paired(ranks_a: list[int | None], ranks_b: list[int | None]) -> dict[str, int]:
    out = {"win": 0, "tie": 0, "loss": 0}
    for a, b in zip(ranks_a, ranks_b):
        out[compare_ranks(a, b)] += 1
    return out


def bootstrap_ci(values: list[float], n_boot: int = BOOTSTRAP_N, seed: int = BOOTSTRAP_SEED, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap interval of the mean, resampling questions with replacement (fixed seed, so reruns are identical)."""
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return means[int(n_boot * alpha / 2)], means[min(n_boot - 1, int(n_boot * (1 - alpha / 2)))]


def tiny_stats(per_query: list[tuple[list[dict], list[str]]], top: int = TOP_CHUNKS, tiny: int = TINY) -> dict:
    """per_query: (ranked chunk hits, expected doc ids). Share of the top-`top` chunks under `tiny` tokens, and how often
    such a chunk belongs to an expected doc (as a share of the tiny chunks, and the number of questions where it happens)."""
    chunks = n_tiny = n_tiny_expected = q_with_tiny_expected = 0
    for hits, expected in per_query:
        top_hits = hits[:top]
        t = [h for h in top_hits if h["token_count"] < tiny]
        te = [h for h in t if h["doc_id"] in expected]
        chunks, n_tiny, n_tiny_expected = chunks + len(top_hits), n_tiny + len(t), n_tiny_expected + len(te)
        q_with_tiny_expected += bool(te)
    return {"top_chunks": chunks, "tiny": n_tiny, "tiny_share": n_tiny / chunks if chunks else 0.0,
            "tiny_from_expected": n_tiny_expected, "tiny_from_expected_share": n_tiny_expected / n_tiny if n_tiny else 0.0,
            "questions_with_tiny_expected": q_with_tiny_expected, "questions": len(per_query)}


def summarize(rows: list[dict]) -> dict:
    out = aggregate(rows)
    if rows:
        out["recall@10_ci95"] = [round(x, 4) for x in bootstrap_ci([r["recall@10"] for r in rows])]
        out["mrr_ci95"] = [round(x, 4) for x in bootstrap_ci([r["rr"] for r in rows])]
    return out


# -- run ----------------------------------------------------------------------------------------
def load_golden(path: str) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf8").splitlines() if l.strip()]


def git_info() -> dict:
    def run(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()
    return {"sha": run("rev-parse", "HEAD"), "dirty_files": [l for l in run("status", "--short").splitlines() if "eval/results" not in l]}


def retrieve_all(es, index, questions, embed, query_of=lambda q: q["question"], modes=MODES, weights=None) -> dict:
    """{(chunker, mode): {question id: ranked chunk hits}}. `query_of` picks the query text (default: the question);
    `weights` ([bm25, dense]) is only for the weighted-RRF sensitivity run (None = plain RRF, the baseline)."""
    out = {}
    for chunker in CHUNKERS:
        for mode in modes:
            per = {}
            for q in questions:
                text = query_of(q)
                if mode == "bm25":
                    per[q["id"]] = bm25(es, index, text, chunker, POOL)
                elif mode == "dense":
                    per[q["id"]] = dense(es, index, embed(text), chunker, POOL)
                else:
                    per[q["id"]] = hybrid(es, index, text, embed(text), chunker, HYBRID_TOP, POOL, weights=weights)
            out[(chunker, mode)] = per
    return out


def score(questions, retrieved, label=lambda chunker, mode: f"{chunker}/{mode}") -> dict:
    rows_out = {}
    types = [t for t in TYPES if any(q["type"] == t for q in questions)]
    for (chunker, mode), per in retrieved.items():
        name = label(chunker, mode)
        qrows = []
        for q in questions:
            hits = per[q["id"]]
            m = evaluate_query(hits, q["expected_doc_ids"], POOL)
            ranks = doc_ranks(hits, q["expected_doc_ids"])
            qrows.append({"id": q["id"], "type": q["type"], **m, "ranks": ranks, "first_rank": first_rank(ranks), "n_chunks": len(hits),
                          "top5": [{"doc_id": h["doc_id"], "tokens": h["token_count"], "expected": h["doc_id"] in q["expected_doc_ids"]} for h in hits[:TOP_CHUNKS]]})
        rows_out[name] = {"overall": summarize(qrows), "by_type": {t: summarize([r for r in qrows if r["type"] == t]) for t in types},
                          "tiny": tiny_stats([(per[q["id"]], q["expected_doc_ids"]) for q in questions]), "questions": qrows}
    return rows_out


def paired_all(results: dict) -> dict:
    out = {}
    for chunker in CHUNKERS:
        h = results[f"{chunker}/hybrid"]["questions"]
        for other in ("bm25", "dense"):
            o = results[f"{chunker}/{other}"]["questions"]
            entry = {"overall": paired([r["first_rank"] for r in h], [r["first_rank"] for r in o])}
            for t in TYPES:
                entry[t] = paired([r["first_rank"] for r in h if r["type"] == t], [r["first_rank"] for r, hr in zip(o, h) if hr["type"] == t])
            out[f"{chunker}: hybrid vs {other}"] = entry
    return out


# -- report -------------------------------------------------------------------------------------
def _f(x):
    return f"{x:.3f}"


def format_md(doc: dict) -> str:
    """Readable report. Rows are whatever `results` holds; the intro and title come from meta (title, intro)."""
    r, m = doc["results"], doc["meta"]
    names = list(r)
    types = list(m["n_by_type"])
    n_all = m["n_answerable"]
    L = [f"# {m.get('title', 'Retrieval baseline')}", "",
         f"Git `{m['git']['sha'][:7]}` | {m['timestamp']} | golden `{m['golden_file']}` (sha256 `{m['golden_sha256'][:12]}`) | "
         f"{n_all} questions scored (" + ", ".join(f"{t} {m['n_by_type'][t]}" for t in types) + f"); {m['n_unanswerable']} unanswerable excluded.", ""]
    if m.get("intro"):
        L += [m["intro"], ""]
    L += ["Doc-level metrics after dedupe. Recall@k = share of expected docs in the top k distinct docs; MRR = mean 1/rank of the first expected doc. "
          "Exhausted lists stay in the denominator as misses. n is small, so read differences with the intervals.", "",
          f"## Overall (n = {n_all} questions per row)", "",
          "| row | n | Recall@5 | Recall@10 | Recall@10 95% CI | MRR | MRR 95% CI | exhausted | exhausted & missed | <10 docs |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n in names:
        o = r[n]["overall"]
        L.append(f"| {n} | {o['n']} | {_f(o['recall@5'])} | {_f(o['recall@10'])} | {o['recall@10_ci95'][0]:.3f}-{o['recall@10_ci95'][1]:.3f} | {_f(o['mrr'])} | "
                 f"{o['mrr_ci95'][0]:.3f}-{o['mrr_ci95'][1]:.3f} | {o['exhausted']} | {o['exhausted_missed']} | {o['short']} |")
    L += ["", "Bootstrap: percentile, 10,000 resamples of the questions, seed 0. A hybrid row is never exhausted by construction (its dense list always fills the window); "
          "its exhausted count is 0 and says nothing about the BM25 half.", "", "## By question type", ""]
    for t in types:
        L += [f"### {t} (n = {m['n_by_type'][t]})", "", "| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |", "|---|---|---|---|---|---|---|"]
        for n in names:
            o = r[n]["by_type"][t]
            L.append(f"| {n} | {o['n']} | {_f(o['recall@5'])} | {_f(o['recall@10'])} | {_f(o['mrr'])} | {o['exhausted']} | {o['exhausted_missed']} |")
        L.append("")
    if doc.get("paired"):
        L += ["## Paired comparison: rank of the first expected doc, hybrid vs a single mode", "",
              "win = hybrid ranks the first expected doc better, loss = worse, tie = same rank (including both missing).", "",
              "| comparison | scope | n | wins | ties | losses |", "|---|---|---|---|---|---|"]
        for k, e in doc["paired"].items():
            for scope in ("overall", *types):
                p = e[scope]
                L.append(f"| {k} | {scope} | {sum(p.values())} | {p['win']} | {p['tie']} | {p['loss']} |")
        L.append("")
    L += [f"## Tiny-chunk diagnostic (top {TOP_CHUNKS} chunks per question, tiny = under {TINY} tokens)", "",
          "| row | top-5 chunks | tiny | tiny share | tiny from an expected doc | share of tiny | questions with one |", "|---|---|---|---|---|---|---|"]
    for n in names:
        t = r[n]["tiny"]
        L.append(f"| {n} | {t['top_chunks']} | {t['tiny']} | {t['tiny_share']:.1%} | {t['tiny_from_expected']} | {t['tiny_from_expected_share']:.1%} | {t['questions_with_tiny_expected']} of {t['questions']} |")
    L += ["", "## Per-question rank of the first expected doc (distinct docs; `-` = not returned)", "",
          "| id | type | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for i, q in enumerate(r[names[0]]["questions"]):
        L.append(f"| {q['id']} | {q['type']} | " + " | ".join(str(r[n]["questions"][i]["first_rank"] or "-") for n in names) + " |")
    if doc.get("extra_md"):
        L += ["", *doc["extra_md"]]
    L += ["", "## Settings", "", "```json", json.dumps(m["settings"], indent=1), "```", ""]
    return "\n".join(L)


def make_meta(es, index, golden_path, golden, questions, model, emb, guard, index_options, extra_settings=None, **extra) -> dict:
    """Provenance and every setting that affects a retrieval number."""
    counts = {c: es.count(index=index, query={"term": {"chunker": c}})["count"] for c in CHUNKERS}
    settings = {"index": index, "es_version": es.info()["version"]["number"], "docs_per_chunker": counts, "embed_model": model,
                "pool": POOL, "knn": {k: v for k, v in knn_clause([], "x").items() if k in ("k", "num_candidates")},
                "rrf_k": RRF_K, "hybrid_fused_list": HYBRID_TOP, "bm25_fields": BM25_FIELDS, "bm25_window": POOL, "ks": list(KS),
                "tiny_chunk_tokens": TINY, "bootstrap": {"n": BOOTSTRAP_N, "seed": BOOTSTRAP_SEED, "method": "percentile, resampling questions"},
                "index_options": index_options, "fusion": "python", "query_embeddings_api_calls_this_run": emb.calls,
                "query_embeddings_est_spend_usd": round(guard.spent, 8), **(extra_settings or {})}
    types = [t for t in TYPES if any(q["type"] == t for q in questions)]
    return {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git": git_info(), "golden_file": golden_path,
            "golden_sha256": hashlib.sha256(Path(golden_path).read_bytes()).hexdigest(), "n_answerable": len(questions),
            "n_unanswerable": len(golden) - len(questions), "n_by_type": {t: sum(q["type"] == t for q in questions) for t in types},
            "settings": settings, **extra}


def main(argv=None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", default="eval/golden.jsonl")
    ap.add_argument("--out-json", default="eval/results/retrieval_baseline.json")
    ap.add_argument("--out-md", default="eval/results/retrieval_baseline.md")
    ap.add_argument("--dry-run", action="store_true", help="print the query-embedding cost estimate and exit (no API call, no search)")
    ap.add_argument("--yes", action="store_true", help="the owner approved the estimate: embed uncached questions without asking")
    a = ap.parse_args(argv)

    golden = load_golden(a.golden)
    questions = [q for q in golden if q["answerable"]]
    model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    index = os.environ.get("ES_INDEX", "rag-docs")
    guard = SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5")))

    def confirm(what, tokens, usd):
        print(f"embedding {what}: {tokens} tokens, est. ${usd:.8f}")
        return a.yes or input("go ahead? [y/N] ").strip().lower() == "y"

    def client():
        from openai import OpenAI
        return OpenAI(max_retries=0)

    emb = QueryEmbedder(f"data/embed_cache/{model}.jsonl", model, client, guard, confirm=confirm)
    texts = [q["question"] for q in questions]
    if a.dry_run:
        todo = [t for t in dict.fromkeys(texts) if not emb.is_cached(t)]
        tokens = sum(emb.estimate(t)[0] for t in todo)
        from ingest.embed_cache import cost_usd
        print(f"{len(questions)} answerable questions, {len(todo)} not yet in the embedding cache\n"
              f"est. tokens={tokens}  est. cost=${cost_usd(model, tokens):.8f}  MAX_SPEND_USD=${guard.max_usd}\ndry run: no API call, no search")
        return 0
    emb.prefetch(texts)  # one batched call for the uncached questions, after confirmation
    es = Elasticsearch(os.environ.get("ES_URL", "http://127.0.0.1:9200"))
    retrieved = retrieve_all(es, index, questions, emb)
    results = score(questions, retrieved)
    meta = make_meta(es, index, a.golden, golden, questions, model, emb, guard,
                     index_options="as built (effective bbq_hnsw, rescore oversample 3.0; eval/results/mapping.json)")
    doc = {"meta": meta, "results": results, "paired": paired_all(results)}
    Path(a.out_json).write_text(json.dumps(doc, indent=1))
    Path(a.out_md).write_text(format_md(doc), encoding="utf8")
    print(f"saved {a.out_json} and {a.out_md}; embedding calls this run: {emb.calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
