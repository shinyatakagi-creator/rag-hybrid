"""python -m eval.failure_analysis  -> eval/results/failure_analysis_data.json

For c009, c010 and c002 (the questions the baseline misses most): where do the expected pages' chunks rank in the BM25 and
dense lists (window 200, chunk level), what does the chunk that actually contains the answer say, which query words does
BM25 match in it, and what ranks first instead. Diagnosis only: the golden set is not changed. Reading is in
eval/results/failure_analysis.md.
"""
import json
import os
import re

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from eval.retrieval_eval import CHUNKERS, load_golden
from ingest.embed_cache import SpendGuard
from rag.retrieve import POOL, QueryEmbedder, bm25, bm25_query, dense

# the sentence that answers each question, found in the expected page's own text (chosen by reading the page)
ANSWER_PHRASES = {
    "c009": {"concepts/cluster-administration/node-autoscaling": "If the requests of a given Pod are too low"},
    "c010": {"tasks/manage-daemon/update-daemon-set": "Some nodes run out of resources"},
    "c002": {"tasks/debug/debug-cluster/resource-usage-monitoring": "metrics-server discovers all nodes",
             "tasks/debug/debug-cluster/resource-metrics-pipeline": "Cluster addon component that collects"},
}


def main() -> None:
    load_dotenv()
    model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    index = os.environ.get("ES_INDEX", "rag-docs")
    emb = QueryEmbedder(f"data/embed_cache/{model}.jsonl", model, lambda: None, SpendGuard(5))  # cached questions only; a miss would fail, no API client
    es = Elasticsearch(os.environ.get("ES_URL", "http://127.0.0.1:9200"))
    golden = {q["id"]: q for q in load_golden("eval/golden.jsonl")}
    chunks = {}
    for line in open("data/chunks/heading.jsonl"):
        c = json.loads(line)
        chunks.setdefault(c["doc_id"], []).append(c)
    for line in open("data/chunks/fixed.jsonl"):
        c = json.loads(line)
        chunks.setdefault(c["doc_id"], []).append(c)
    out = {}
    for qid, phrases in ANSWER_PHRASES.items():
        q = golden[qid]
        vec = emb(q["question"])
        out[qid] = {"question": q["question"], "expected": q["expected_doc_ids"], "by_chunker": {}}
        for chunker in CHUNKERS:
            lists = {"bm25": bm25(es, index, q["question"], chunker, POOL), "dense": dense(es, index, vec, chunker, POOL)}
            entry = {}
            for mode, hits in lists.items():
                ids = [h["_id"] for h in hits]
                e = {"window": len(hits), "top3": [{"doc_id": h["doc_id"], "heading": h["heading_path"], "tokens": h["token_count"]} for h in hits[:3]], "pages": {}}
                for doc in q["expected_doc_ids"]:
                    ranks = [(r, h) for r, h in enumerate(hits, 1) if h["doc_id"] == doc]
                    ans = next((c for c in chunks[doc] if c["chunker"] == chunker and phrases.get(doc, "\0") in re.sub(r"\s+", " ", c["content"])), None) if doc in phrases else None
                    page = {"best_chunk_rank": ranks[0][0] if ranks else None, "best_chunk": (ranks[0][1]["heading_path"], ranks[0][1]["token_count"]) if ranks else None,
                            "chunks_of_page_in_window": len(ranks)}
                    if ans:
                        page["answer_chunk"] = {"heading": ans["heading_path"], "tokens": ans["token_count"], "text": ans["content"][:700],
                                                "rank_in_list": ids.index(ans["chunk_id"]) + 1 if ans["chunk_id"] in ids else None}
                        if mode == "bm25":
                            ex = es.explain(index=index, id=ans["chunk_id"], query=bm25_query(q["question"], chunker))["explanation"]
                            terms = sorted(set(re.findall(r"weight\((?:[\w.]+):([^ ]+) in", json.dumps(ex))))
                            page["answer_chunk"]["bm25_matched_terms"] = terms
                    e["pages"][doc] = page
                entry[mode] = e
            out[qid]["by_chunker"][chunker] = entry
    json.dump(out, open("eval/results/failure_analysis_data.json", "w"), indent=1)
    print("saved eval/results/failure_analysis_data.json")


if __name__ == "__main__":
    main()
