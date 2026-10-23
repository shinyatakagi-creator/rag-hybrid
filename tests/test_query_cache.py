import random
import threading

import pytest

from ingest.embed_cache import EmbedCache, SpendGuard, cache_key
from rag.query_cache import QueryCache, pack, scan_ingestion, serving_path, unpack, warm
from rag.retrieve import QueryEmbedder

MODEL = "text-embedding-3-small"


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.embeddings = self

    def create(self, model, input):
        from types import SimpleNamespace
        self.calls += 1
        return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=[float(len(t))] * 4) for i, t in enumerate(input)], usage=SimpleNamespace(total_tokens=len(input)))


def test_vectors_round_trip_bit_exactly_including_awkward_floats(tmp_path):
    rng = random.Random(1)
    vec = [rng.uniform(-1, 1) for _ in range(1536)] + [0.1, 1e-300, -0.0, 1.7976931348623157e308, 5e-324, 1 / 3]
    assert unpack(pack(vec)) == vec
    c = QueryCache(tmp_path / "q.sqlite")
    c.put_many({"k": vec}, MODEL, 1542)
    got = c.get("k")
    assert got == vec and [repr(x) for x in got] == [repr(x) for x in vec]  # same floats, same text (so JSON-equal)
    assert c.get("missing") is None and c.has("k") and not c.has("missing") and c.count() == 1


def test_cache_survives_reopen_and_overwrites_a_key(tmp_path):
    p = tmp_path / "q.sqlite"
    QueryCache(p).put_many({"a": [1.0, 2.0]}, MODEL, 2)
    c = QueryCache(p)
    assert c.get("a") == [1.0, 2.0]
    c.put_many({"a": [3.0, 4.0]}, MODEL, 2)
    assert c.get("a") == [3.0, 4.0] and c.count() == 1


def test_concurrent_lookups_are_safe(tmp_path):
    c = QueryCache(tmp_path / "q.sqlite")
    c.put_many({f"k{i}": [float(i)] * 8 for i in range(50)}, MODEL, 8)
    errors = []

    def work():
        try:
            for i in range(50):
                assert c.get(f"k{i}") == [float(i)] * 8
        except Exception as e:  # pragma: no cover
            errors.append(e)

    ts = [threading.Thread(target=work) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errors


def test_embedder_writes_only_the_serving_cache_and_never_the_ingestion_file(tmp_path):
    ing = tmp_path / "ing.jsonl"
    EmbedCache(ing).add_many({cache_key(MODEL, 4, "from ingestion"): [9.0] * 4})
    before = ing.read_bytes()
    client = FakeClient()
    e = QueryEmbedder(ing, MODEL, lambda: client, SpendGuard(5), dims=4)
    assert e("from ingestion") == [9.0] * 4 and client.calls == 0  # found in the ingestion file, copied to the serving cache
    v = e("brand new query")
    assert client.calls == 1 and ing.read_bytes() == before  # the new vector went to sqlite only
    assert serving_path(ing).exists() and QueryCache(serving_path(ing)).get(cache_key(MODEL, 4, "brand new query")) == v
    assert QueryCache(serving_path(ing)).get(cache_key(MODEL, 4, "from ingestion")) == [9.0] * 4


def test_second_process_hits_the_serving_cache_without_reading_the_ingestion_file(tmp_path):
    ing = tmp_path / "ing.jsonl"
    EmbedCache(ing).add_many({cache_key(MODEL, 4, "q one"): [1.0] * 4})
    client = FakeClient()
    QueryEmbedder(ing, MODEL, lambda: client, SpendGuard(5), dims=4)("q one")  # copies into sqlite
    ing.unlink()  # the big file is gone: only the serving cache can answer now
    e2 = QueryEmbedder(ing, MODEL, lambda: client, SpendGuard(5), dims=4, legacy_fallback=False)
    assert e2("q one") == [1.0] * 4 and client.calls == 0 and e2.calls == 0


def test_serving_mode_does_not_consult_the_ingestion_file_at_all(tmp_path):
    ing = tmp_path / "ing.jsonl"
    EmbedCache(ing).add_many({cache_key(MODEL, 4, "only in ingestion"): [7.0] * 4})
    client = FakeClient()
    e = QueryEmbedder(ing, MODEL, lambda: client, SpendGuard(5), dims=4, legacy_fallback=False)
    assert e("only in ingestion") == [17.0] * 4 and client.calls == 1  # a miss goes to the embedding call, not to the big file (the ingestion value 7.0 is not used)


def test_key_scheme_matches_the_ingestion_cache(tmp_path):
    c = QueryCache(tmp_path / "q.sqlite")
    k = cache_key("text-embedding-3-small", 1536, "How do I drain a node?")
    c.put_many({k: [0.5]}, "text-embedding-3-small", 1536)
    assert c.get(k) == [0.5] and len(k) == 64
    assert cache_key("text-embedding-3-small", 1536, "How do I drain a node? ") != k  # exact text matters


def test_warm_copies_known_vectors_reports_missing_and_leaves_ingestion_alone(tmp_path):
    ing = tmp_path / "ing.jsonl"
    EmbedCache(ing).add_many({cache_key(MODEL, 4, "a"): [1.0] * 4, cache_key(MODEL, 4, "b"): [2.0] * 4})
    before = ing.read_bytes()
    c = QueryCache(tmp_path / "q.sqlite")
    assert warm(c, ing, MODEL, 4, ["a", "b", "c", "a"]) == {"requested": 3, "already_in_serving_cache": 0, "copied_from_ingestion": 2, "missing": 1}
    assert warm(c, ing, MODEL, 4, ["a", "b", "c"]) == {"requested": 3, "already_in_serving_cache": 2, "copied_from_ingestion": 0, "missing": 1}
    assert ing.read_bytes() == before and c.get(cache_key(MODEL, 4, "b")) == [2.0] * 4


def test_scan_ingestion_is_read_only_and_tolerates_a_missing_file(tmp_path):
    assert scan_ingestion(tmp_path / "nope.jsonl", {"x" * 64}) == {}
