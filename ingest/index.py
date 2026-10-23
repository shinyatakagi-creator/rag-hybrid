"""python -m ingest.index [--dry-run] [--yes] [--recreate]

Embeds chunk texts (cached on disk) and bulk-indexes both chunkers into one ES index.
--dry-run prints unique texts / tokens / estimated cost and exits without any API call.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

from .chunkers import embed_text
from .embed_cache import BudgetExceeded, EmbedCache, SpendGuard, cache_key, cost_usd, embed_missing

DIMS = 1536
MAPPING = {
    "properties": {
        "doc_id": {"type": "keyword"},
        "chunker": {"type": "keyword"},
        "url": {"type": "keyword"},
        "title": {"type": "text"},
        "heading_path": {"type": "text"},
        "content": {"type": "text", "analyzer": "english"},
        "token_count": {"type": "integer"},
        "position": {"type": "integer"},
        "embedding": {"type": "dense_vector", "dims": DIMS, "similarity": "cosine", "index": True},
    }
}
SETTINGS = {"number_of_shards": 1, "number_of_replicas": 0}  # single node: no unassigned replicas


def load_chunks(chunks_dir: Path) -> dict[str, list[dict]]:
    out = {}
    for name in ("fixed", "heading"):
        p = Path(chunks_dir) / f"{name}.jsonl"
        if p.exists():
            out[name] = [json.loads(l) for l in p.read_text(encoding="utf8").splitlines()]
    return out


def plan(chunks_by_name: dict[str, list[dict]], cache: EmbedCache, model: str, max_usd: float) -> dict:
    """What an embedding run would cost. No API call."""
    uniq = {}
    for chunks in chunks_by_name.values():
        for c in chunks:
            uniq.setdefault(embed_text(c), c["token_count"])
    todo = {t: n for t, n in uniq.items() if cache_key(model, DIMS, t) not in cache.vectors}
    tokens = sum(todo.values())
    return {
        "chunks": {k: len(v) for k, v in chunks_by_name.items()},
        "unique_texts": len(uniq),
        "cached": len(uniq) - len(todo),
        "to_embed": len(todo),
        "tokens_to_embed": tokens,
        "est_cost_usd": cost_usd(model, tokens),
        "max_spend_usd": max_usd,
        "within_budget": cost_usd(model, tokens) <= max_usd,
    }


def print_plan(p: dict, model: str) -> None:
    print(f"model={model} dims={DIMS}  chunks={p['chunks']}")
    print(f"unique texts={p['unique_texts']:,}  already cached={p['cached']:,}  to embed={p['to_embed']:,}")
    print(f"tokens to embed={p['tokens_to_embed']:,}  estimated cost=${p['est_cost_usd']:.4f}  "
          f"MAX_SPEND_USD=${p['max_spend_usd']}  within budget={p['within_budget']}")


def create_index(es: Elasticsearch, index: str, recreate: bool, index_options: dict | None = None) -> None:
    """`index_options` (e.g. {"type": "hnsw", "m": 16, "ef_construction": 100}) sets the embedding field's index_options
    explicitly; None leaves the ES default (bbq_hnsw for 1536 dims on ES 9.5), which is what rag-docs uses."""
    if recreate and es.indices.exists(index=index):
        es.indices.delete(index=index)
    if not es.indices.exists(index=index):
        mappings = json.loads(json.dumps(MAPPING))
        if index_options:
            mappings["properties"]["embedding"]["index_options"] = index_options
        es.indices.create(index=index, mappings=mappings, settings=SETTINGS)


def bulk_index(es: Elasticsearch, index: str, chunks_by_name: dict, cache: EmbedCache, model: str) -> int:
    def actions():
        for chunks in chunks_by_name.values():
            for c in chunks:
                src = {k: c[k] for k in ("doc_id", "chunker", "url", "title", "heading_path", "content", "token_count", "position")}
                src["embedding"] = cache.vectors[cache_key(model, DIMS, embed_text(c))]
                yield {"_index": index, "_id": c["chunk_id"], "_source": src}

    ok, _ = helpers.bulk(es.options(request_timeout=120), actions(), chunk_size=500)
    es.indices.refresh(index=index)
    return ok


def save_mapping(es: Elasticsearch, index: str, path: Path) -> dict:
    """Saved mapping includes defaults for `embedding`, so the effective index_options are visible."""
    out = {
        "mapping": es.indices.get_mapping(index=index).body,
        "embedding_with_defaults": es.indices.get_field_mapping(fields="embedding", index=index, include_defaults=True).body,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(out, indent=1))
    return out


def report_counts(es: Elasticsearch, index: str, chunks_by_name: dict) -> bool:
    ok = True
    for name, chunks in chunks_by_name.items():
        n = es.count(index=index, query={"term": {"chunker": name}})["count"]
        ok &= n == len(chunks)
        print(f"  {name:8} ES docs={n:5}  chunk file={len(chunks):5}  {'OK' if n == len(chunks) else 'MISMATCH'}")
    return ok


def main(argv=None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks-dir", default="data/chunks")
    ap.add_argument("--cache", default=None, help="default data/embed_cache/<model>.jsonl")
    ap.add_argument("--mapping-out", default="eval/results/mapping.json")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and exit; no API call")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    ap.add_argument("--index-options", help='JSON for the embedding field index_options, e.g. \'{"type":"hnsw","m":16,"ef_construction":100}\'; default: ES default')
    ap.add_argument("--recreate", action="store_true", help="drop and recreate the index first")
    a = ap.parse_args(argv)

    model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    index = os.environ.get("ES_INDEX", "rag-docs")
    max_usd = float(os.environ.get("MAX_SPEND_USD", "5"))
    cache = EmbedCache(a.cache or f"data/embed_cache/{model}.jsonl")
    chunks_by_name = load_chunks(Path(a.chunks_dir))
    p = plan(chunks_by_name, cache, model, max_usd)
    print_plan(p, model)
    if a.dry_run:
        print("dry run: no API call made")
        return 0
    if not p["within_budget"]:
        print("ABORT: estimated cost exceeds MAX_SPEND_USD")
        return 2

    calls = 0
    if p["to_embed"]:
        if not a.yes and input("Proceed with the paid embedding run? [y/N] ").strip().lower() != "y":
            print("cancelled")
            return 1
        from openai import OpenAI

        client = OpenAI(max_retries=0)  # retries are handled (and tested) in embed_cache
        guard = SpendGuard(max_usd)
        try:
            calls = embed_missing([embed_text(c) for ch in chunks_by_name.values() for c in ch], cache, model, DIMS, client, guard)
        except BudgetExceeded as e:
            print(f"ABORT: {e}")
            return 2
        est, act = p["tokens_to_embed"], guard.api_tokens
        diff = (act - est) / est
        usage = {"calls": calls, "estimated_tokens": est, "api_reported_tokens": act, "diff": round(diff, 4),
                 "estimated_cost_usd": cost_usd(model, est), "actual_cost_usd": cost_usd(model, act)}
        Path("eval/results").mkdir(parents=True, exist_ok=True)
        Path("eval/results/embed_run.json").write_text(json.dumps(usage, indent=1))
        print(f"embedding calls made: {calls}")
        print(f"API usage: {act:,} tokens = ${usage['actual_cost_usd']:.4f}  vs estimate {est:,} = ${usage['estimated_cost_usd']:.4f}  "
              f"({diff:+.2%}){'  ** FLAG: differs by more than 5% **' if abs(diff) > 0.05 else ''}")
    else:
        print("embedding calls made: 0 (everything cached)")

    es = Elasticsearch(os.environ.get("ES_URL", "http://127.0.0.1:9200"))
    create_index(es, index, a.recreate, json.loads(a.index_options) if a.index_options else None)
    n = bulk_index(es, index, chunks_by_name, cache, model)
    print(f"bulk indexed {n} docs into {index}")
    good = report_counts(es, index, chunks_by_name)
    save_mapping(es, index, Path(a.mapping_out))
    print(f"mapping saved to {a.mapping_out}")
    return 0 if good else 3


if __name__ == "__main__":
    sys.exit(main())
