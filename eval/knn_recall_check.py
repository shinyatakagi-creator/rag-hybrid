"""python -m eval.knn_recall_check: overlap of ES kNN top-10/top-50 with exact brute-force cosine, per (k, num_candidates).

Exact = cosine over the cached full-precision vectors. Uses the same proxy queries as eval.pool_check (already cached)."""
import json
import math
import os

from elasticsearch import Elasticsearch

from eval.pool_check import proxy_queries
from ingest.chunkers import embed_text
from ingest.embed_cache import EmbedCache, SpendGuard, cache_key
from rag.retrieve import EXCLUDE, QueryEmbedder, knn_clause

M = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
path = f"data/embed_cache/{M}.jsonl"
es = Elasticsearch("http://127.0.0.1:9200")
emb = QueryEmbedder(path, M, lambda: None, SpendGuard(0))  # cached queries only; any miss would fail, no API call possible
cache = EmbedCache(path)
chunks = [json.loads(l) for l in open("data/chunks/heading.jsonl", encoding="utf8")]
unit = lambda v: [x / math.sqrt(sum(y * y for y in v)) for x in v]
vecs = {c["chunk_id"]: unit(cache.vectors[cache_key(M, 1536, embed_text(c))]) for c in chunks}
queries = proxy_queries("data/chunks/heading.jsonl", 100)[:40]
cfgs = [(50, 200), (50, 800), (100, 400), (200, 800), (200, 2000)]
tot = {c: [0, 0] for c in cfgs}
for q in queries:
    qv = unit(emb(q))
    exact = sorted(vecs, key=lambda i: -sum(a * b for a, b in zip(qv, vecs[i])))
    for k, nc in cfgs:
        kn = {**knn_clause(qv, "heading", k=k), "num_candidates": nc}
        got = [h["_id"] for h in es.search(index="rag-docs", knn=kn, size=50, source_excludes=EXCLUDE)["hits"]["hits"]]
        tot[(k, nc)][0] += len(set(got[:10]) & set(exact[:10])) / 10
        tot[(k, nc)][1] += len(set(got[:50]) & set(exact[:50])) / 50
print(f"{len(queries)} proxy queries, heading chunker. Mean overlap with exact brute-force cosine:")
for (k, nc), (a, b) in tot.items():
    print(f"  k={k:4d} num_candidates={nc:5d}   top-10: {a / len(queries):.3f}   top-50: {b / len(queries):.3f}")
