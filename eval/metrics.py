"""Retrieval metrics on distinct docs, with the exhausted-list rule.

A retriever list is *exhausted* when it returned fewer chunks than the window asked for: every chunk that matches has
already been returned, so no larger window could help (typical for BM25 on rare identifiers). Rule (owner decision):
an exhausted query stays in the metric as an ordinary query (expected doc not returned = miss, recall 0); the number
of exhausted queries is reported separately and never excluded from the denominator.
"""
from rag.retrieve import POOL, distinct_docs

KS = (5, 10)
MIN_DOCS = 10  # a list with fewer distinct docs than this cannot fill recall@10 (reported as `short`)


def list_exhausted(hits: list[dict], window: int = POOL) -> bool:
    return len(hits) < window


def evaluate_query(hits: list[dict], expected: list[str], window: int = POOL, ks=KS) -> dict:
    """Metrics for one answerable query from a ranked chunk list. Chunk hits are collapsed to distinct docs first."""
    if not expected:
        raise ValueError("expected_doc_ids is empty: unanswerable questions have no retrieval metrics")
    ranked = [h["doc_id"] for h in distinct_docs(hits)]
    want = set(expected)
    row = {f"recall@{k}": len(want & set(ranked[:k])) / len(want) for k in ks}
    row["rr"] = next((1 / r for r, d in enumerate(ranked, 1) if d in want), 0.0)
    row["distinct_docs"] = len(ranked)
    row["exhausted"] = list_exhausted(hits, window)
    return row


def aggregate(rows: list[dict], ks=KS) -> dict:
    """Mean recall@k and MRR over *all* rows (exhausted ones included), plus separate counts."""
    n = len(rows)
    if n == 0:
        return {"n": 0}
    out = {"n": n, "mrr": sum(r["rr"] for r in rows) / n}
    out.update({f"recall@{k}": sum(r[f"recall@{k}"] for r in rows) / n for k in ks})
    out["exhausted"] = sum(r["exhausted"] for r in rows)
    out["exhausted_share"] = out["exhausted"] / n
    out["exhausted_missed"] = sum(r["exhausted"] and r["rr"] == 0.0 for r in rows)  # exhausted AND expected doc not returned
    out["short"] = sum(r["distinct_docs"] < MIN_DOCS for r in rows)  # < 10 distinct docs returned, any cause
    return out
