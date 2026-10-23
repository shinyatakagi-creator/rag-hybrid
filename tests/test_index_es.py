"""Indexing against a live ES (skipped if none): fake vectors, throwaway index, no OpenAI call."""
import pytest
from elasticsearch import Elasticsearch

from ingest.chunkers import fixed_chunks, heading_chunks
from ingest.embed_cache import EmbedCache, SpendGuard, embed_missing
from ingest.chunkers import embed_text
from ingest.index import DIMS, bulk_index, create_index, plan, report_counts, save_mapping
from ingest.loaders import Doc
from tests.test_embed import FakeClient

INDEX = "rag-test-phase2"
MODEL = "text-embedding-3-small"


@pytest.fixture()
def es():
    c = Elasticsearch("http://127.0.0.1:9200", request_timeout=5)
    try:
        c.info()
    except Exception:
        pytest.skip("no Elasticsearch on 127.0.0.1:9200")
    yield c
    c.indices.delete(index=INDEX, ignore_unavailable=True)


def test_index_counts_match_chunk_files_and_rerun_embeds_nothing(es, tmp_path):
    words = " ".join(["alpha"] * 150)
    docs = [Doc(f"concepts/d{i}", f"https://kubernetes.io/docs/concepts/d{i}/", f"D{i}", f"## A\n{words}\n## B\n{words}") for i in range(5)]
    chunks = {"fixed": [c for d in docs for c in fixed_chunks(d)], "heading": [c for d in docs for c in heading_chunks(d)]}
    cache = EmbedCache(tmp_path / "c.jsonl")
    client = FakeClient(dims=DIMS)
    texts = [embed_text(c) for ch in chunks.values() for c in ch]
    assert embed_missing(texts, cache, MODEL, DIMS, client, SpendGuard(5)) >= 1
    create_index(es, INDEX, recreate=True)
    bulk_index(es, INDEX, chunks, cache, MODEL)
    assert report_counts(es, INDEX, chunks)

    # second run: nothing to embed, same doc counts (idempotent _id = chunk_id)
    cache2, again = EmbedCache(tmp_path / "c.jsonl"), FakeClient(dims=DIMS)
    assert plan(chunks, cache2, MODEL, 5)["to_embed"] == 0
    assert embed_missing(texts, cache2, MODEL, DIMS, again, SpendGuard(5)) == 0 and again.calls == 0
    bulk_index(es, INDEX, chunks, cache2, MODEL)
    assert report_counts(es, INDEX, chunks)

    saved = save_mapping(es, INDEX, tmp_path / "mapping.json")
    assert saved["mapping"][INDEX]["mappings"]["properties"]["embedding"]["dims"] == DIMS
