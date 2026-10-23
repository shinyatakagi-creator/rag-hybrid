"""python -m eval.pool_check [--n 100] [--pools 50,100,200]

How many queries get fewer than 10 distinct docs from each retriever window? Uses proxy queries (page titles and
leaf headings sampled with a fixed seed), NOT the golden set. Only paid call: one batched query embedding run,
after a confirmation prompt. Output is saved by the caller under eval/results/.
"""
import argparse
import json
import os
import random
import re
import statistics
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from ingest.embed_cache import SpendGuard
from rag.retrieve import QueryEmbedder, bm25, dense, distinct_docs, rrf

MIN_DOCS = 10


def proxy_queries(chunks_path: str, n: int, seed: int = 0) -> list[str]:
    rows = [json.loads(l) for l in open(chunks_path, encoding="utf8")]
    titles = sorted({r["title"] for r in rows})
    leaves = sorted({r["heading_path"].split(" > ")[-1] for r in rows if " > " in r["heading_path"]})
    clean = lambda s: re.sub(r"\s*\{#[^}]*\}", "", s).replace("`", "").strip()
    rng = random.Random(seed)
    qs = [clean(s) for s in rng.sample(titles, n // 2) + rng.sample(leaves, n - n // 2)]
    return list(dict.fromkeys(q for q in qs if len(q) > 2))


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--pools", default="50,100,200")
    a = ap.parse_args()
    model, index = os.environ.get("EMBED_MODEL", "text-embedding-3-small"), os.environ.get("ES_INDEX", "rag-docs")

    def confirm(what, tokens, usd):
        return input(f"Embed {what} ({tokens} tokens, est. ${usd:.8f})? [y/N] ").strip().lower() == "y"

    def client():
        from openai import OpenAI
        return OpenAI(max_retries=0)

    emb = QueryEmbedder(f"data/embed_cache/{model}.jsonl", model, client, SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5"))), confirm=confirm)
    queries = proxy_queries("data/chunks/heading.jsonl", a.n)
    emb.prefetch(queries)
    es = Elasticsearch(os.environ.get("ES_URL", "http://127.0.0.1:9200"))
    print(f"{len(queries)} proxy queries (titles + leaf headings, seed 0); embedding calls: {emb.calls}")
    print(f"threshold: fewer than {MIN_DOCS} distinct docs.  Cells: queries below threshold / min / median distinct docs")
    for chunker in ("fixed", "heading"):
        for pool in (int(p) for p in a.pools.split(",")):
            row = {m: [] for m in ("bm25", "dense", "hybrid")}
            for q in queries:
                b, d = bm25(es, index, q, chunker, pool), dense(es, index, emb(q), chunker, pool)
                row["bm25"].append(len(distinct_docs(b)))
                row["dense"].append(len(distinct_docs(d)))
                row["hybrid"].append(len(distinct_docs(rrf([b, d], top_n=2 * pool))))  # whole fused list, not top-k
            cells = "  ".join(f"{m}: {sum(x < MIN_DOCS for x in v):3d}/{min(v):3d}/{statistics.median(v):5.1f}" for m, v in row.items())
            print(f"  {chunker:8} pool={pool:4d}  {cells}")


if __name__ == "__main__":
    main()
