import json
from fractions import Fraction

import pytest
from elasticsearch import Elasticsearch

from ingest.chunkers import embed_text, fixed_chunks, heading_chunks
from ingest.embed_cache import BudgetExceeded, EmbedCache, SpendGuard, cache_key, embed_missing
from ingest.index import DIMS, bulk_index, create_index
from ingest.loaders import Doc
from rag.retrieve import (
    NUM_CANDIDATES, POOL, QueryEmbedder, bm25_query, distinct_docs, knn_clause, rrf, search,
)
from tests.test_embed import FakeClient

MODEL = "text-embedding-3-small"


def hits(*ids):
    return [{"_id": i, "doc_id": f"d-{i}", "score": 0.0} for i in ids]


def ids(result):
    return [h["_id"] for h in result]


# -- RRF, hand-computed (k=60) --------------------------------------------------------------
def test_doc_in_one_list_only_scores_one_over_k_plus_rank():
    out = rrf([hits("a", "b"), []], k=60, top_n=8)
    assert ids(out) == ["a", "b"]
    assert out[0]["score"] == pytest.approx(1 / 61) and out[1]["score"] == pytest.approx(1 / 62)
    assert out[0]["ranks"] == {"list0": 1, "list1": None}


def test_doc_in_both_lists_beats_doc_first_in_only_one():
    # a: rank 1 + rank 2 = 1/61 + 1/62 = 0.032522 ; c: rank 1 in list1 only = 1/61 = 0.016393 ; b: rank 2 in list0 only = 1/62 = 0.016129
    out = rrf([hits("a", "b"), hits("c", "a")], k=60)
    assert ids(out) == ["a", "c", "b"]
    assert [round(h["score"], 6) for h in out] == [0.032522, 0.016393, 0.016129]


def test_exact_ties_keep_first_seen_order():
    # a: 1/61 + 1/62 ; b: 1/62 + 1/61 -> exactly equal; c and d tie at 1/63
    out = rrf([hits("a", "b", "c"), hits("b", "a", "d")], k=60)
    assert ids(out) == ["a", "b", "c", "d"]
    assert out[0]["score"] == out[1]["score"] == pytest.approx(1 / 61 + 1 / 62)
    assert out[2]["score"] == out[3]["score"] == pytest.approx(1 / 63)


def test_empty_inputs():
    assert rrf([], k=60) == []
    assert rrf([[], []], k=60) == []
    assert ids(rrf([[], hits("x")], k=60)) == ["x"]


def test_duplicate_id_in_one_list_counts_once_at_best_rank():
    out = rrf([hits("a", "b", "a")], k=60)
    assert ids(out) == ["a", "b"] and out[0]["score"] == pytest.approx(1 / 61)


def test_top_n_truncates_and_k_changes_scores():
    assert ids(rrf([hits("a", "b", "c")], k=60, top_n=2)) == ["a", "b"]
    assert rrf([hits("a")], k=10)[0]["score"] == pytest.approx(1 / 11)


def test_scores_are_exact_fractions_so_float_order_cannot_flip_ties():
    many = [hits(*"abcdefg"), hits(*"gfedcba"), hits(*"bcdefga")]
    out = rrf(many, k=60, top_n=7)
    exact = {i: sum(Fraction(1, 60 + l.index(i) + 1) for l in [[h["_id"] for h in x] for x in many]) for i in "abcdefg"}
    assert [exact[i] for i in ids(out)] == sorted(exact.values(), reverse=True)


# -- query builders ----------------------------------------------------------------------------
def test_query_bodies_carry_chunker_filter_and_spec_parameters():
    q = bm25_query("flag", "heading")
    assert q["bool"]["filter"] == {"term": {"chunker": "heading"}}
    assert q["bool"]["must"]["multi_match"]["fields"] == ["title^2", "heading_path^1.5", "content"]
    kn = knn_clause([0.0] * 3, "fixed")
    assert (kn["k"], kn["num_candidates"], POOL, NUM_CANDIDATES) == (200, 800, 200, 200)
    assert knn_clause([0.0] * 3, "fixed", k=50)["num_candidates"] == 200  # the original 50 / 200 spec is the same ratio
    assert kn["filter"] == {"term": {"chunker": "fixed"}}


def test_distinct_docs_keeps_best_chunk_per_doc_in_rank_order():
    h = [{"_id": "1", "doc_id": "a"}, {"_id": "2", "doc_id": "a"}, {"_id": "3", "doc_id": "b"}, {"_id": "4", "doc_id": "a"}, {"_id": "5", "doc_id": "c"}]
    assert [x["_id"] for x in distinct_docs(h)] == ["1", "3", "5"]
    assert [x["doc_id"] for x in distinct_docs(h, 2)] == ["a", "b"]
    assert distinct_docs([]) == []


def test_prefetch_embeds_only_uncached_queries_in_one_call(tmp_path):
    path = tmp_path / "c.jsonl"
    EmbedCache(path).add_many({cache_key(MODEL, 4, "already"): [1.0] * 4})
    client = FakeClient()
    seen = []
    e = QueryEmbedder(path, MODEL, lambda: client, SpendGuard(5), dims=4, confirm=lambda what, tok, usd: seen.append((what, tok)) or True)
    assert e.prefetch(["already", "new one", "new two", "new one"]) == 1
    assert client.calls == 1 and seen[0][0] == "2 queries"  # one confirmation, one batch, duplicates and cached skipped
    assert e("new two") and e.prefetch(["already", "new one"]) == 0 and client.calls == 1


# -- query-embedding cache -------------------------------------------------------------------
def make_embedder(tmp_path, client, max_usd=5.0, name="c.jsonl"):
    return QueryEmbedder(tmp_path / name, MODEL, lambda: client, SpendGuard(max_usd), dims=4)


def test_query_embedding_is_cached_in_memory_and_on_disk(tmp_path):
    client = FakeClient()
    e = make_embedder(tmp_path, client)
    v1 = e("how do I drain a node")
    assert e("how do I drain a node") == v1 and client.calls == 1
    e2 = make_embedder(tmp_path, client)  # new process: finds it by scanning the file
    assert e2("how do I drain a node") == v1 and client.calls == 1 and e2.calls == 0
    e2("a different query")
    assert client.calls == 2


def test_query_key_is_model_dims_exact_text_and_shared_with_ingestion(tmp_path):
    path = tmp_path / "c.jsonl"
    EmbedCache(path).add_many({cache_key(MODEL, 4, "the exact text"): [9.0, 9.0, 9.0, 9.0]})  # as written by ingestion
    client = FakeClient()
    e = make_embedder(tmp_path, client)
    assert e("the exact text") == [9.0, 9.0, 9.0, 9.0] and client.calls == 0
    e("the exact text ")  # a trailing space is a different key
    assert client.calls == 1


def test_query_embedding_uses_the_spend_guard(tmp_path):
    client = FakeClient()
    with pytest.raises(BudgetExceeded):
        make_embedder(tmp_path, client, max_usd=1e-12)("some query that costs more than that")
    assert client.calls == 0


def test_query_embedding_can_be_declined(tmp_path):
    client = FakeClient()
    e = QueryEmbedder(tmp_path / "c.jsonl", MODEL, lambda: client, SpendGuard(5), dims=4, confirm=lambda *a: False)
    with pytest.raises(SystemExit):
        e("q")
    assert client.calls == 0


# -- chunker filter never leaks (live ES, throwaway index, fake vectors) ----------------------
INDEX = "rag-test-phase3"


@pytest.fixture()
def es_with_both_chunkers(tmp_path):
    es = Elasticsearch("http://127.0.0.1:9200", request_timeout=10)
    try:
        es.info()
    except Exception:
        pytest.skip("no Elasticsearch on 127.0.0.1:9200")
    body = " ".join(["kubelet flag inflight requests"] * 40)
    docs = [Doc(f"concepts/d{i}", f"https://k8s/d{i}/", f"Doc {i}", f"## A\n{body}\n## B\n{body} extra{i}") for i in range(6)]
    chunks = {"fixed": [c for d in docs for c in fixed_chunks(d)], "heading": [c for d in docs for c in heading_chunks(d)]}
    cache = EmbedCache(tmp_path / "c.jsonl")
    embed_missing([embed_text(c) for ch in chunks.values() for c in ch], cache, MODEL, DIMS, FakeClient(dims=DIMS), SpendGuard(5))
    create_index(es, INDEX, recreate=True)
    bulk_index(es, INDEX, chunks, cache, MODEL)
    yield es
    es.indices.delete(index=INDEX, ignore_unavailable=True)


@pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid"])
@pytest.mark.parametrize("chunker", ["fixed", "heading"])
def test_chunker_filter_never_leaks_other_chunker(es_with_both_chunkers, mode, chunker):
    embed = lambda text: [1.0] * DIMS
    result = search(es_with_both_chunkers, INDEX, "kubelet inflight requests", mode, chunker, k=20, embed=embed)
    assert result, f"{mode}/{chunker} returned nothing"
    assert {h["chunker"] for h in result} == {chunker}
    other = "heading" if chunker == "fixed" else "fixed"
    assert not {h["_id"] for h in result} & {h["_id"] for h in es_with_both_chunkers.search(
        index=INDEX, query={"term": {"chunker": other}}, size=1000)["hits"]["hits"]}
