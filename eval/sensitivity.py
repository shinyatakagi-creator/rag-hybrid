"""Sensitivity analyses on top of the frozen baseline (reported as sensitivity analysis, not tuning; there is no held-out set).

    python -m eval.sensitivity bare-term [--dry-run] [--yes]   # exact term alone as the query (exact_term + mixed questions)
    python -m eval.sensitivity rrf-weights                     # hybrid with dense weight 1, 1.5, 2 (bm25 weight 1)
    python -m eval.sensitivity index-options                   # dense + hybrid on rag-docs (bbq_hnsw) vs rag-docs-hnsw (explicit hnsw)

Each writes its own eval/results/<name>.json and .md with provenance and every setting. The golden set is not changed.
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from eval.retrieval_eval import (CHUNKERS, TYPES, doc_ranks, first_rank, format_md, git_info, load_golden, make_meta, paired, retrieve_all, score)
from ingest.embed_cache import SpendGuard, cost_usd
from rag.retrieve import POOL, QueryEmbedder

WEIGHTS = (1, 1.5, 2)  # dense weight; bm25 weight is always 1
HNSW_INDEX = "rag-docs-hnsw"
HNSW_OPTIONS = {"type": "hnsw", "m": 16, "ef_construction": 100}


def top_chunk_agreement(a: dict, b: dict, k: int = 10) -> float:
    """Mean share of the top-k chunk ids that two ranked-chunk-list dicts (question id -> hits) have in common."""
    shares = [len({h["_id"] for h in a[q][:k]} & {h["_id"] for h in b[q][:k]}) / k for q in a]
    return sum(shares) / len(shares)


def _write(out: str, doc: dict) -> None:
    Path(out + ".json").write_text(json.dumps(doc, indent=1))
    Path(out + ".md").write_text(format_md(doc), encoding="utf8")
    print(f"saved {out}.json and {out}.md")


def _setup(a):
    load_dotenv()
    golden = load_golden(a.golden)
    model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    guard = SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5")))

    def confirm(what, tokens, usd):
        print(f"embedding {what}: {tokens} tokens, est. ${usd:.8f}")
        return a.yes or input("go ahead? [y/N] ").strip().lower() == "y"

    def client():
        from openai import OpenAI
        return OpenAI(max_retries=0)

    emb = QueryEmbedder(f"data/embed_cache/{model}.jsonl", model, client, guard, confirm=confirm)
    es = Elasticsearch(os.environ.get("ES_URL", "http://127.0.0.1:9200"))
    return golden, model, guard, emb, es, os.environ.get("ES_INDEX", "rag-docs")


def cmd_bare_term(a) -> int:
    golden, model, guard, emb, es, index = _setup(a)
    questions = [q for q in golden if q["answerable"] and q["type"] in ("exact_term", "mixed")]
    texts = [q["exact_term"] for q in questions]
    if a.dry_run:
        todo = [t for t in dict.fromkeys(texts) if not emb.is_cached(t)]
        tokens = sum(emb.estimate(t)[0] for t in todo)
        print(f"{len(questions)} bare-term queries, {len(todo)} not yet in the embedding cache\n"
              f"est. tokens={tokens}  est. cost=${cost_usd(model, tokens):.8f}  MAX_SPEND_USD=${guard.max_usd}\ndry run: no API call, no search")
        return 0
    emb.prefetch(texts)
    retrieved = retrieve_all(es, index, questions, emb, query_of=lambda q: q["exact_term"])
    meta = make_meta(es, index, a.golden, golden, questions, model, emb, guard, "as built (effective bbq_hnsw)",
                     extra_settings={"query": "the question's exact_term field alone, e.g. '--root-ca-file'", "queries": {q["id"]: q["exact_term"] for q in questions}},
                     title="Bare-term diagnostic (sensitivity analysis, not part of the golden-set baseline)",
                     intro="Query = the exact term alone, for the 16 exact_term and mixed questions; same 6 rows, same metrics, same expected docs. "
                           "It shows how much of the baseline score on these questions comes from the surrounding words.")
    _write(a.out or "eval/results/bare_term", {"meta": meta, "results": score(questions, retrieved), "paired": {}})
    return 0


def cmd_rrf_weights(a) -> int:
    golden, model, guard, emb, es, index = _setup(a)
    questions = [q for q in golden if q["answerable"]]
    texts = [q["question"] for q in questions]
    emb.prefetch(texts)  # all cached after the baseline: 0 calls
    retrieved = retrieve_all(es, index, questions, emb, modes=("bm25", "dense"))
    labels = {}
    for w in WEIGHTS:
        part = retrieve_all(es, index, questions, emb, modes=("hybrid",), weights=[1, w])
        for (c, _), per in part.items():
            retrieved[(c, f"hybrid w{w}")] = per
    results = score(questions, retrieved, label=lambda c, m: f"{c}/{m}")
    extra = ["## Weighted RRF: change in the rank of the first expected doc relative to weight 1 (the baseline fusion)", "",
             "Reported for every weight; no weight is picked. wins = the weighted fusion ranks the first expected doc better than weight 1.", "",
             "| chunker | dense weight | wins | ties | losses |", "|---|---|---|---|---|"]
    for c in CHUNKERS:
        base = [r["first_rank"] for r in results[f"{c}/hybrid w1"]["questions"]]
        for w in WEIGHTS[1:]:
            p = paired([r["first_rank"] for r in results[f"{c}/hybrid w{w}"]["questions"]], base)
            extra.append(f"| {c} | {w} | {p['win']} | {p['tie']} | {p['loss']} |")
    base_doc = json.loads(Path("eval/results/retrieval_baseline.json").read_text())["results"]
    same = all(results[f"{c}/hybrid w1"]["questions"] == base_doc[f"{c}/hybrid"]["questions"] for c in CHUNKERS)
    meta = make_meta(es, index, a.golden, golden, questions, model, emb, guard, "as built (effective bbq_hnsw)",
                     extra_settings={"dense_weights": list(WEIGHTS), "bm25_weight": 1, "weight_1_reproduces_baseline_hybrid": same},
                     title="Weighted RRF sensitivity (not tuning; no weight is chosen)",
                     intro="Hybrid = Python RRF (k=60) with the dense list weighted 1, 1.5 or 2 and the BM25 list weighted 1. Weight 1 is the baseline fusion "
                           f"(reproduces the baseline hybrid rows exactly: {same}). bm25 and dense rows are repeated for reference.")
    _write(a.out or "eval/results/rrf_weights", {"meta": meta, "results": results, "paired": {}, "extra_md": extra})
    return 0


def cmd_index_options(a) -> int:
    golden, model, guard, emb, es, index = _setup(a)
    if not es.indices.exists(index=HNSW_INDEX):
        print(f"{HNSW_INDEX} does not exist: build it with ES_INDEX={HNSW_INDEX} python -m ingest.index --yes --index-options '{json.dumps(HNSW_OPTIONS)}'")
        return 1
    questions = [q for q in golden if q["answerable"]]
    emb.prefetch([q["question"] for q in questions])
    results, runs = {}, {}
    for idx, tag in ((index, "bbq_hnsw"), (HNSW_INDEX, "hnsw")):
        ret = retrieve_all(es, idx, questions, emb, modes=("dense", "hybrid"))
        runs[tag] = ret
        results.update(score(questions, ret, label=lambda c, m, tag=tag: f"{c}/{m} [{tag}]"))
    extra = ["## Agreement between the two indexes", "", "Mean share of the top-10 chunk ids two indexes return for the same query (dense list and fused hybrid list).", "",
             "| chunker | mode | top-10 chunk overlap | questions with a different first expected-doc rank |", "|---|---|---|---|"]
    for c in CHUNKERS:
        for m in ("dense", "hybrid"):
            ra, rb = results[f"{c}/{m} [bbq_hnsw]"]["questions"], results[f"{c}/{m} [hnsw]"]["questions"]
            diff = sum(x["first_rank"] != y["first_rank"] for x, y in zip(ra, rb))
            extra.append(f"| {c} | {m} | {top_chunk_agreement(runs['bbq_hnsw'][(c, m)], runs['hnsw'][(c, m)]):.3f} | {diff} of {len(ra)} |")
    sizes = {i: es.indices.stats(index=i)["_all"]["primaries"]["store"]["size_in_bytes"] for i in (index, HNSW_INDEX)}
    meta = make_meta(es, index, a.golden, golden, questions, model, emb, guard, "compared: rag-docs = default (effective bbq_hnsw, m16, ef100, rescore oversample 3.0) vs rag-docs-hnsw = explicit hnsw (m16, ef_construction 100, no quantisation)",
                     extra_settings={"hnsw_index": HNSW_INDEX, "hnsw_options": HNSW_OPTIONS, "store_bytes": sizes, "mapping_hnsw": "eval/results/mapping_hnsw.json",
                                     "query_time": f"kNN k={POOL}, num_candidates=800 on both indexes"},
                     title="index_options sensitivity: bbq_hnsw (as built) vs explicit hnsw",
                     intro="Same chunks and vectors (from the embedding cache, 0 embedding calls), same queries and settings; only the dense_vector index_options differ. "
                           "BM25 does not depend on it, so only dense and hybrid rows are compared.")
    _write(a.out or "eval/results/index_options", {"meta": meta, "results": results, "paired": {}, "extra_md": extra})
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bare-term", "rrf-weights", "index-options"])
    ap.add_argument("--golden", default="eval/golden.jsonl")
    ap.add_argument("--out", help="output path without extension (default eval/results/<name>)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="the owner approved the embedding estimate")
    a = ap.parse_args(argv)
    return {"bare-term": cmd_bare_term, "rrf-weights": cmd_rrf_weights, "index-options": cmd_index_options}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
