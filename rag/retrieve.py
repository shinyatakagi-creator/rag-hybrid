"""Retrieval over the rag-docs index: bm25, dense, hybrid (own Python RRF), filtered by chunker.

    python -m rag.retrieve --query "..." --mode all --chunker both --k 5 [--dry-run]

The native `rrf` retriever is intentionally not used here (needs a trial licence, later checkpoint).
"""
import argparse
import json
import os
from fractions import Fraction

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from ingest.embed_cache import EmbedCache, SpendGuard, cache_key, cost_usd, count_tokens, embed_missing

DIMS = 1536
POOL = 50  # size of each inner list fed to RRF (and the kNN k)
NUM_CANDIDATES = 200
RRF_K = 60
BM25_FIELDS = ["title^2", "heading_path^1.5", "content"]
EXCLUDE = ["embedding"]  # never ship 1536 floats back


# -- query builders (pure, unit-tested) ------------------------------------------------
def chunker_filter(chunker: str) -> dict:
    return {"term": {"chunker": chunker}}


def bm25_query(q: str, chunker: str) -> dict:
    return {"bool": {"must": {"multi_match": {"query": q, "fields": BM25_FIELDS}}, "filter": chunker_filter(chunker)}}


def knn_clause(vec: list[float], chunker: str) -> dict:
    return {"field": "embedding", "query_vector": vec, "k": POOL, "num_candidates": NUM_CANDIDATES, "filter": chunker_filter(chunker)}


def _hit(h: dict) -> dict:
    s = h["_source"]
    return {
        "_id": h["_id"], "chunk_id": h["_id"], "doc_id": s["doc_id"], "score": h["_score"],
        "heading_path": s["heading_path"], "chunker": s["chunker"], "url": s["url"], "title": s["title"],
        "content": s["content"], "token_count": s["token_count"],
    }


# -- the three modes ---------------------------------------------------------------------
def bm25(es: Elasticsearch, index: str, q: str, chunker: str, size: int = POOL) -> list[dict]:
    r = es.search(index=index, query=bm25_query(q, chunker), size=size, source_excludes=EXCLUDE)
    return [_hit(h) for h in r["hits"]["hits"]]


def dense(es: Elasticsearch, index: str, vec: list[float], chunker: str, size: int = POOL) -> list[dict]:
    r = es.search(index=index, knn=knn_clause(vec, chunker), size=size, source_excludes=EXCLUDE)
    return [_hit(h) for h in r["hits"]["hits"]]


def rrf(result_lists: list[list[dict]], k: int = RRF_K, top_n: int = 8, names: list[str] | None = None) -> list[dict]:
    """Reciprocal rank fusion: score(d) = sum over lists of 1 / (k + rank), rank starting at 1.

    A hit repeated inside one list counts once, at its best rank. Scores are summed as exact fractions so
    ties are real ties; ties keep first-seen order (list order, then rank). Each returned hit is the first
    copy seen, with `score` replaced by the RRF score and `ranks` giving its rank per input list (None if absent)."""
    names = names or [f"list{i}" for i in range(len(result_lists))]
    scores: dict[str, Fraction] = {}
    first: dict[str, dict] = {}
    ranks: dict[str, dict] = {}
    for name, results in zip(names, result_lists):
        seen = set()
        for rank, hit in enumerate(results, start=1):
            i = hit["_id"]
            if i in seen:
                continue
            seen.add(i)
            scores[i] = scores.get(i, Fraction(0)) + Fraction(1, k + rank)
            first.setdefault(i, hit)
            ranks.setdefault(i, {n: None for n in names})[name] = rank
    order = sorted(scores, key=lambda i: scores[i], reverse=True)  # stable: ties keep first-seen order
    return [{**first[i], "score": float(scores[i]), "ranks": ranks[i]} for i in order[:top_n]]


def hybrid(es: Elasticsearch, index: str, q: str, vec: list[float], chunker: str, k: int = 8) -> list[dict]:
    lists = [bm25(es, index, q, chunker, POOL), dense(es, index, vec, chunker, POOL)]
    return rrf(lists, RRF_K, k, names=["bm25", "dense"])


def search(es: Elasticsearch, index: str, query: str, mode: str, chunker: str, k: int = 8, embed=None) -> list[dict]:
    """mode: bm25 | dense | hybrid. `embed` is a text -> vector callable (needed for dense and hybrid)."""
    if mode == "bm25":
        return bm25(es, index, query, chunker, k)
    if mode not in ("dense", "hybrid"):
        raise ValueError(f"unknown mode {mode!r}")
    vec = embed(query)
    return dense(es, index, vec, chunker, k) if mode == "dense" else hybrid(es, index, query, vec, chunker, k)


# -- query embeddings: same cache file, key and spend guard as ingestion -----------------------
class QueryEmbedder:
    """Embeds a query through the ingestion cache (key = model + dims + exact text) and spend guard.

    The cache file (hundreds of MB) is not loaded into memory: a miss in the small in-process dict is
    answered by streaming the file for the key. New queries are appended to the same file."""

    def __init__(self, cache_path, model: str, client_factory, guard: SpendGuard, dims: int = DIMS, confirm=None):
        self.path, self.model, self.dims, self.guard = cache_path, model, dims, guard
        self.client_factory, self.confirm, self.client = client_factory, confirm, None
        self.cache = EmbedCache(cache_path, load=False)
        self.calls = 0

    def _scan(self, key: str) -> list[float] | None:
        needle = f'{{"k": "{key}"'
        try:
            with open(self.path, encoding="utf8") as f:
                for line in f:
                    if line.startswith(needle):
                        return json.loads(line)["v"]
        except FileNotFoundError:
            pass
        return None

    def is_cached(self, text: str) -> bool:
        key = cache_key(self.model, self.dims, text)
        if key in self.cache.vectors:
            return True
        vec = self._scan(key)
        if vec is not None:
            self.cache.vectors[key] = vec
        return vec is not None

    def estimate(self, text: str) -> tuple[int, float]:
        tokens = count_tokens(text)
        return tokens, cost_usd(self.model, tokens)

    def __call__(self, text: str) -> list[float]:
        if not self.is_cached(text):
            if self.confirm and not self.confirm(text, *self.estimate(text)):
                raise SystemExit("cancelled")
            self.client = self.client or self.client_factory()
            self.calls += embed_missing([text], self.cache, self.model, self.dims, self.client, self.guard)
        return self.cache.vectors[cache_key(self.model, self.dims, text)]


# -- CLI -----------------------------------------------------------------------------------------
def _print(mode: str, chunker: str, hits: list[dict]) -> None:
    print(f"\n[{chunker} / {mode}]")
    if not hits:
        print("  (no results)")
    for r, h in enumerate(hits, 1):
        extra = f"  ranks={h['ranks']}" if "ranks" in h else ""
        print(f"  {r}. {h['doc_id']}  score={h['score']:.4f}  tok={h['token_count']}  | {h['heading_path']}{extra}")


def main(argv=None) -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--mode", choices=["bm25", "dense", "hybrid", "all"], default="all")
    ap.add_argument("--chunker", choices=["fixed", "heading", "both"], default="both")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true", help="print the query-embedding estimate and exit; no API call")
    a = ap.parse_args(argv)

    model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    index = os.environ.get("ES_INDEX", "rag-docs")
    guard = SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5")))

    def confirm(text, tokens, usd):
        return input(f"Embed query ({tokens} tokens, est. ${usd:.8f})? [y/N] ").strip().lower() == "y"

    def client():
        from openai import OpenAI
        return OpenAI(max_retries=0)

    emb = QueryEmbedder(f"data/embed_cache/{model}.jsonl", model, client, guard, confirm=confirm)
    modes = ["bm25", "dense", "hybrid"] if a.mode == "all" else [a.mode]
    chunkers = ["fixed", "heading"] if a.chunker == "both" else [a.chunker]
    if a.dry_run:
        tokens, usd = emb.estimate(a.query)
        need = any(m != "bm25" for m in modes) and not emb.is_cached(a.query)
        print(f"query={a.query!r}\ntokens={tokens}  est. cost=${usd:.8f}  already cached={emb.is_cached(a.query)}  "
              f"API call needed={need}  MAX_SPEND_USD=${guard.max_usd}\ndry run: no API call made")
        return
    es = Elasticsearch(os.environ.get("ES_URL", "http://127.0.0.1:9200"))
    print(f"query: {a.query!r}")
    for chunker in chunkers:
        for mode in modes:
            _print(mode, chunker, search(es, index, a.query, mode, chunker, a.k, embed=emb))
    print(f"\nembedding calls made: {emb.calls}  est. spend ${guard.spent:.8f}")


if __name__ == "__main__":
    main()
