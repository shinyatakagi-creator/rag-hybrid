import httpx
import openai
import pytest

from ingest.embed_cache import (
    BudgetExceeded, EmbedCache, SpendGuard, cache_key, cost_usd, count_tokens, embed_missing,
)

DIMS = 4  # tiny vectors; real runs use 1536
MODEL = "text-embedding-3-small"


class FakeClient:
    """Mimics client.embeddings.create; optionally raises scripted errors first."""

    def __init__(self, errors=(), dims=DIMS):
        self.calls, self.errors, self.dims = 0, list(errors), dims
        self.embeddings = self

    def create(self, model, input):
        if self.errors:
            raise self.errors.pop(0)
        self.calls += 1
        data = [type("D", (), {"index": i, "embedding": [float(len(t))] * self.dims})() for i, t in enumerate(input)]
        return type("R", (), {"data": data})()


def rate_limit(code=None):
    resp = httpx.Response(429, request=httpx.Request("POST", "http://x"))
    return openai.RateLimitError("429", response=resp, body={"code": code} if code else None)


def texts(n):
    return [f"chunk text number {i} " + "word " * 20 for i in range(n)]


def test_cache_key_depends_on_model_dims_and_exact_text():
    k = cache_key(MODEL, 1536, "a")
    assert k == cache_key(MODEL, 1536, "a")
    assert len({k, cache_key("other", 1536, "a"), cache_key(MODEL, 384, "a"), cache_key(MODEL, 1536, "a ")}) == 4


def test_max_spend_aborts_before_any_api_call(tmp_path):
    client, cache = FakeClient(), EmbedCache(tmp_path / "c.jsonl")
    with pytest.raises(BudgetExceeded):
        embed_missing(texts(10), cache, MODEL, DIMS, client, SpendGuard(max_usd=1e-9))
    assert client.calls == 0 and not cache.vectors  # nothing was sent, nothing cached


def test_max_spend_stops_mid_run_and_keeps_what_was_paid_for(tmp_path):
    ts = texts(30)  # 3 batches of 10
    per_batch = cost_usd(MODEL, sum(count_tokens(t) for t in ts[:10]))
    client, cache = FakeClient(), EmbedCache(tmp_path / "c.jsonl")
    with pytest.raises(BudgetExceeded):
        embed_missing(ts, cache, MODEL, DIMS, client, SpendGuard(max_usd=per_batch * 2.5), batch_size=10)
    assert client.calls == 2 and len(cache.vectors) == 20
    assert len(EmbedCache(tmp_path / "c.jsonl").vectors) == 20  # persisted to disk after each batch


def test_second_run_makes_zero_calls(tmp_path):
    ts, client = texts(25), FakeClient()
    cache = EmbedCache(tmp_path / "c.jsonl")
    assert embed_missing(ts, cache, MODEL, DIMS, client, SpendGuard(5), batch_size=10) == 3
    again = FakeClient()
    assert embed_missing(ts, EmbedCache(tmp_path / "c.jsonl"), MODEL, DIMS, again, SpendGuard(5), batch_size=10) == 0
    assert again.calls == 0


def test_duplicate_texts_are_embedded_once(tmp_path):
    client = FakeClient()
    embed_missing(["same", "same", "same"], EmbedCache(tmp_path / "c.jsonl"), MODEL, DIMS, client, SpendGuard(5))
    assert client.calls == 1


def test_batches_of_100_by_default(tmp_path):
    client = FakeClient()
    assert embed_missing(texts(250), EmbedCache(tmp_path / "c.jsonl"), MODEL, DIMS, client, SpendGuard(5)) == 3


def test_429_is_retried_with_growing_backoff(tmp_path):
    client, waits = FakeClient(errors=[rate_limit(), rate_limit()]), []
    embed_missing(texts(3), EmbedCache(tmp_path / "c.jsonl"), MODEL, DIMS, client, SpendGuard(5), sleep=waits.append)
    assert client.calls == 1 and len(waits) == 2 and 1 <= waits[0] < 2 and 2 <= waits[1] < 3


def test_429_retry_does_not_double_charge(tmp_path):
    guard = SpendGuard(5)
    embed_missing(texts(3), EmbedCache(tmp_path / "c.jsonl"), MODEL, DIMS, FakeClient(errors=[rate_limit()] * 3), guard, sleep=lambda s: None)
    solo = SpendGuard(5)
    embed_missing(texts(3), EmbedCache(tmp_path / "d.jsonl"), MODEL, DIMS, FakeClient(), solo)
    assert guard.spent == solo.spent


def test_insufficient_quota_is_not_retried(tmp_path):
    client, waits = FakeClient(errors=[rate_limit("insufficient_quota")]), []
    with pytest.raises(openai.RateLimitError):
        embed_missing(texts(3), EmbedCache(tmp_path / "c.jsonl"), MODEL, DIMS, client, SpendGuard(5), sleep=waits.append)
    assert waits == []


def test_gives_up_after_max_retries(tmp_path):
    client = FakeClient(errors=[rate_limit()] * 20)
    with pytest.raises(openai.RateLimitError):
        embed_missing(texts(3), EmbedCache(tmp_path / "c.jsonl"), MODEL, DIMS, client, SpendGuard(5), sleep=lambda s: None)


def test_unknown_model_has_no_price():
    with pytest.raises(ValueError):
        cost_usd("mystery-embed", 1000)
