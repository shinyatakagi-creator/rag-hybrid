#!/usr/bin/env bash
# Demo against the running API container (127.0.0.1:8000): three illustrative queries, each searched in
# bm25, dense and hybrid mode. Only /search is called (never /ask). Picks come from the saved per-question
# results by fixed rules, so the output is deterministic. BM25 calls are free; dense and hybrid pay one
# query embedding each (about $0.0000002).
#
#   scripts/demo.sh           dry run: show the picks, the calls and the cost ceiling, call nothing
#   scripts/demo.sh --yes     run the calls
#   API=http://127.0.0.1:8000 scripts/demo.sh --yes
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 - "$@" <<'PY'
import hashlib
import json
import os
import sys
import urllib.request

API = os.environ.get("API", "http://127.0.0.1:8000")
CHUNKER, K, TOP = "heading", 50, 3
EMBED_USD = 2e-7  # per query embedding, from docs/SETUP.md
FILES = {"bare": "eval/results/bare_term.json", "base": "eval/results/retrieval_baseline.json", "golden": "eval/golden.jsonl"}
BIG = 10**6  # rank of a page that is not in the list


def load(p):
    return json.load(open(p))


bare, base = load(FILES["bare"]), load(FILES["base"])
golden = {q["id"]: q for q in map(json.loads, open(FILES["golden"]))}


def ranks(res, qtype=None):
    """question id -> first expected-page rank (distinct docs) for heading/<mode>, BIG if not found."""
    return {m: {q["id"]: (q["first_rank"] or BIG) for q in res["results"][f"heading/{m}"]["questions"] if qtype in (None, q["type"])}
            for m in ("bm25", "dense", "hybrid")}


rb, rc = ranks(bare), ranks(base, "conceptual")

# pick 1: bare term, dense misses the top 10, BM25 and hybrid find it; best worst-case rank of the two, then id
p1 = sorted((i for i in rb["dense"] if rb["dense"][i] > 10 and rb["bm25"][i] <= 10 and rb["hybrid"][i] <= 10),
            key=lambda i: (max(rb["bm25"][i], rb["hybrid"][i]), i))[0]
# pick 2: conceptual, BM25 misses the top 10, dense and hybrid find it; best worst-case rank of the two, then id
p2 = sorted((i for i in rc["bm25"] if rc["bm25"][i] > 10 and rc["dense"][i] <= 10 and rc["hybrid"][i] <= 10),
            key=lambda i: (max(rc["dense"][i], rc["hybrid"][i]), i))[0]
# pick 3: conceptual that dense ranks in its top 10 and hybrid ranks worse; largest gap (hybrid miss counts as a loss), then id
p3 = sorted((i for i in rc["dense"] if rc["dense"][i] <= 10 and rc["hybrid"][i] > rc["dense"][i]),
            key=lambda i: (-(rc["hybrid"][i] - rc["dense"][i]), i))[0]

PICKS = [
    ("1. bare term: dense misses the top 10, BM25 and hybrid find the page", p1, bare["meta"]["settings"]["queries"][p1], rb,
     "eval/results/bare_term.json, rows heading/{bm25,dense,hybrid}, first_rank"),
    ("2. conceptual: BM25 misses the top 10, dense and hybrid find the page", p2, golden[p2]["question"], rc,
     "eval/results/retrieval_baseline.json, rows heading/{bm25,dense,hybrid}, first_rank"),
    ("3. conceptual: hybrid ranks the page worse than dense (a loss, shown on purpose)", p3, golden[p3]["question"], rc,
     "eval/results/retrieval_baseline.json, rows heading/{bm25,dense,hybrid}, first_rank"),
]


def fmt(r):
    return "not found" if r >= BIG else str(r)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


print("illustrative picks; the tables in the README are the evidence\n")
print(f"settings: api={API} chunker={CHUNKER} k={K} (chunks) top={TOP} modes=bm25,dense,hybrid endpoint=/search only")
print("inputs:   " + ", ".join(f"{p} (sha256 {sha(p)})" for p in FILES.values()))
print("rank:     saved = first expected page among distinct docs in the saved evaluation (200-chunk window);")
print(f"          live  = same measure over the {K} chunks this call returns ('not found' if beyond them)\n")
for title, qid, query, r, src in PICKS:
    exp = golden[qid]["expected_doc_ids"]
    print(f"{title}\n  question {qid}: {query!r}\n  expected: {', '.join(exp)}\n  picked from {src}")
    print("  saved ranks: " + ", ".join(f"{m}={fmt(r[m][qid])}" for m in ("bm25", "dense", "hybrid")))
n_paid = 2 * len(PICKS)
print(f"\ncalls: {len(PICKS) * 3} /search ({len(PICKS) * 3 - n_paid} bm25, free; {n_paid} dense/hybrid, one query embedding each)")
print(f"cost ceiling: {n_paid} x ${EMBED_USD:.7f} = ${n_paid * EMBED_USD:.7f} "
      f"(about ${len(PICKS) * EMBED_USD:.7f} if hybrid reuses the embedding that dense just cached). No /ask calls.")
if "--yes" not in sys.argv[1:]:
    print("\ndry run: nothing was called. Re-run with --yes to run the calls.")
    sys.exit(0)


def search(query, mode):
    req = urllib.request.Request(f"{API}/search", json.dumps({"query": query, "mode": mode, "chunker": CHUNKER, "k": K}).encode(),
                                 {"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


print("\n--- live results ---")
total = 0.0
for title, qid, query, r, _ in PICKS:
    exp = set(golden[qid]["expected_doc_ids"])
    print(f"\n{title}\n  {qid}: {query!r}")
    for mode in ("bm25", "dense", "hybrid"):
        out = search(query, mode)
        total += out["cost_usd"]
        docs = []
        for h in out["results"]:
            if h["doc_id"] not in docs:
                docs.append(h["doc_id"])
        live = next((i for i, d in enumerate(docs, 1) if d in exp), BIG)
        print(f"  {mode:6} expected page: live rank {fmt(live)} (saved {fmt(r[mode][qid])}); top {TOP}: "
              + "; ".join(("*" if d in exp else "") + d for d in docs[:TOP]))
print(f"\n(* = an expected page) total cost reported by the API: ${total:.7f}")
PY
