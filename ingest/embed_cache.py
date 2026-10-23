"""On-disk embedding cache (jsonl) + spend guard + batched embedding with 429 backoff.

Cache key = sha256(model + dims + exact embedded text), so changing the heading-path prefix,
chunk size or model never reuses a stale vector (see NOTES.md).
"""
import hashlib
import json
import random
import time
from pathlib import Path

import openai
import tiktoken

# USD per 1M input tokens, standard (non-batch) price. Source: developers.openai.com/api/docs/pricing,
# checked 2026-10-23. A model not listed here is refused rather than guessed.
PRICE_PER_M = {"text-embedding-3-small": 0.02}
BATCH_SIZE = 100
MAX_RETRIES = 6
_ENC = tiktoken.get_encoding("cl100k_base")


class BudgetExceeded(RuntimeError):
    pass


class SpendGuard:
    """Running total of estimated spend for this run; aborts before a call that would pass the limit."""

    def __init__(self, max_usd: float):
        self.max_usd, self.spent = max_usd, 0.0
        self.api_tokens = 0  # tokens the API reported in response.usage, summed over batches

    def charge(self, usd: float, what: str = "call") -> None:
        if self.spent + usd > self.max_usd + 1e-12:
            raise BudgetExceeded(
                f"MAX_SPEND_USD={self.max_usd} would be exceeded by {what}: spent ${self.spent:.6f} + ${usd:.6f}"
            )
        self.spent += usd


def cost_usd(model: str, tokens: int) -> float:
    if model not in PRICE_PER_M:
        raise ValueError(f"no verified price for {model!r}; add it to PRICE_PER_M before embedding")
    return tokens / 1e6 * PRICE_PER_M[model]


def count_tokens(text: str) -> int:
    return len(_ENC.encode(text, disallowed_special=()))


def cache_key(model: str, dims: int, text: str) -> str:
    return hashlib.sha256(f"{model}\x00{dims}\x00{text}".encode()).hexdigest()


class EmbedCache:
    def __init__(self, path: Path, load: bool = True):
        self.path = Path(path)
        self.vectors: dict[str, list[float]] = {}
        if load and self.path.exists():  # load=False: append-only handle that never reads the big file
            for line in self.path.read_text(encoding="utf8").splitlines():
                rec = json.loads(line)
                self.vectors[rec["k"]] = rec["v"]

    def add_many(self, items: dict[str, list[float]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf8") as f:
            for k, v in items.items():
                f.write(json.dumps({"k": k, "v": v}) + "\n")
        self.vectors.update(items)


def _embed_batch(client, model: str, batch: list[str], sleep) -> tuple[list[list[float]], int]:
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.embeddings.create(model=model, input=batch)
            usage = getattr(resp, "usage", None)
            return [d.embedding for d in sorted(resp.data, key=lambda d: d.index)], getattr(usage, "total_tokens", 0)
        except openai.RateLimitError as e:
            if getattr(e, "code", None) == "insufficient_quota" or attempt == MAX_RETRIES:
                raise  # out of credit is not a transient 429
            sleep(min(2**attempt, 60) + random.random())


def embed_missing(texts: list[str], cache: EmbedCache, model: str, dims: int, client, guard: SpendGuard,
                  batch_size: int = BATCH_SIZE, sleep=time.sleep) -> int:
    """Embed texts not in the cache, in batches; returns the number of API calls made.

    Each batch is charged to the guard *before* the call and written to the cache right after it,
    so an abort or crash loses nothing already paid for."""
    todo = list(dict.fromkeys(t for t in texts if cache_key(model, dims, t) not in cache.vectors))
    calls = 0
    for i in range(0, len(todo), batch_size):
        batch = todo[i : i + batch_size]
        guard.charge(cost_usd(model, sum(count_tokens(t) for t in batch)), f"batch {i // batch_size + 1}")
        vecs, used = _embed_batch(client, model, batch, sleep)
        guard.api_tokens += used
        calls += 1
        assert all(len(v) == dims for v in vecs), f"expected {dims}-dim vectors, got {len(vecs[0])}"
        cache.add_many({cache_key(model, dims, t): v for t, v in zip(batch, vecs)})
    return calls
