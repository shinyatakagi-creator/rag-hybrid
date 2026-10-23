"""Small serving-side query-embedding cache (sqlite). Separate from the ingestion cache, which it never writes.

Key = sha256(model + dims + exact query text), the same scheme as ingest.embed_cache.cache_key, so a vector copied from the
ingestion cache keeps its key. Vectors are stored as little-endian float64, the exact Python floats the JSON cache holds, so a
lookup returns bit-identical values and cannot change a retrieval result. The file is opened per process; lookups are indexed
(primary key), so a hit costs microseconds instead of a pass over the 273 MB ingestion file.

    python -m rag.query_cache warm --golden eval/golden.jsonl [--field exact_term]   # one-time: copy vectors for known queries out of the ingestion cache
    python -m rag.query_cache stats
"""
import argparse
import json
import sqlite3
import struct
import threading
from datetime import datetime, timezone
from pathlib import Path

from ingest.embed_cache import cache_key


def pack(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}d", *vec)


def unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 8}d", blob))


class QueryCache:
    """sqlite-backed key -> vector store. Thread-safe for the single connection (FastAPI workers share one object)."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS queries (key TEXT PRIMARY KEY, model TEXT NOT NULL, dims INTEGER NOT NULL, vec BLOB NOT NULL, created TEXT NOT NULL) WITHOUT ROWID")
        self._db.commit()

    def get(self, key: str) -> list[float] | None:
        with self._lock:
            row = self._db.execute("SELECT vec FROM queries WHERE key = ?", (key,)).fetchone()
        return unpack(row[0]) if row else None

    def has(self, key: str) -> bool:
        with self._lock:
            return self._db.execute("SELECT 1 FROM queries WHERE key = ?", (key,)).fetchone() is not None

    def put_many(self, items: dict[str, list[float]], model: str, dims: int) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock:
            self._db.executemany("INSERT OR REPLACE INTO queries (key, model, dims, vec, created) VALUES (?, ?, ?, ?, ?)",
                                 [(k, model, dims, pack(v), now) for k, v in items.items()])
            self._db.commit()

    def count(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM queries").fetchone()[0]

    def close(self) -> None:
        with self._lock:
            self._db.close()


def serving_path(ingestion_cache_path) -> Path:
    """Default location: next to the ingestion cache but a different file, e.g. data/embed_cache/<model>.queries.sqlite."""
    p = Path(ingestion_cache_path)
    return p.with_name(p.stem + ".queries.sqlite")


def scan_ingestion(path, keys: set[str]) -> dict[str, list[float]]:
    """Read-only single pass over the ingestion jsonl for the wanted keys (lines look like {"k": "<64 hex>", "v": [...]})."""
    found, start = {}, len('{"k": "')
    try:
        with open(path, encoding="utf8") as f:
            for line in f:
                k = line[start : start + 64]
                if k in keys:
                    found[k] = json.loads(line)["v"]
                    if len(found) == len(keys):
                        break
    except FileNotFoundError:
        pass
    return found


def warm(cache: QueryCache, ingestion_path, model: str, dims: int, texts: list[str]) -> dict:
    """Copy vectors for `texts` that already exist in the ingestion cache into the serving cache. Makes no API call and never
    writes the ingestion cache. Returns counts."""
    keys = {cache_key(model, dims, t): t for t in dict.fromkeys(texts)}
    todo = {k for k in keys if not cache.has(k)}
    found = scan_ingestion(ingestion_path, todo) if todo else {}
    if found:
        cache.put_many(found, model, dims)
    return {"requested": len(keys), "already_in_serving_cache": len(keys) - len(todo), "copied_from_ingestion": len(found), "missing": len(todo) - len(found)}


def main(argv=None) -> int:
    import os

    from dotenv import load_dotenv
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["warm", "stats"])
    ap.add_argument("--golden", default="eval/golden.jsonl")
    ap.add_argument("--field", default="question", help="which golden field to warm: question or exact_term")
    a = ap.parse_args(argv)
    model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    ing = f"data/embed_cache/{model}.jsonl"
    cache = QueryCache(serving_path(ing))
    if a.cmd == "stats":
        print(f"{cache.path}: {cache.count()} vectors")
        return 0
    texts = [q[a.field] for q in map(json.loads, Path(a.golden).read_text(encoding="utf8").splitlines()) if q.get(a.field)]
    print(json.dumps(warm(cache, ing, model, 1536, texts)), f"-> {cache.count()} vectors in {cache.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
