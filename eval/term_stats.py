"""How many chunks and docs contain a term, per chunker? For checking that an exact-term question points to a small set of pages.

    python -m eval.term_stats --term=--max-requests-inflight --term=maxUnavailable
    python -m eval.term_stats -- --max-requests-inflight        # '--' lets a term start with a dash
    python -m eval.term_stats --term=CrashLoopBackOff --show 10 --case

Matching is a literal substring on the cleaned chunk text (case-insensitive unless --case), not BM25 tokens. It reports
chunks whose content contains the term, docs those chunks belong to, and docs whose heading_path (which BM25 boosts)
contains it. Reads data/chunks/*.jsonl; needs no Elasticsearch and no API.
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def load_chunks(chunks_dir: str = "data/chunks") -> dict[str, list[dict]]:
    return {n: [json.loads(l) for l in open(Path(chunks_dir) / f"{n}.jsonl", encoding="utf8")] for n in ("fixed", "heading")}


def term_stats(term: str, chunks_by_name: dict[str, list[dict]], case: bool = False) -> dict[str, dict]:
    norm = (lambda s: s) if case else str.lower
    t = norm(term)
    out = {}
    for name, chunks in chunks_by_name.items():
        hit = [c for c in chunks if t in norm(c["content"])]
        per_doc = Counter(c["doc_id"] for c in hit)
        out[name] = {
            "chunks": len(hit),
            "docs": len(per_doc),
            "per_doc": per_doc.most_common(),
            "docs_in_heading_path": len({c["doc_id"] for c in chunks if t in norm(c["heading_path"])}),
        }
    return out


def report(term: str, stats: dict[str, dict], show: int = 8) -> str:
    lines = [f"term {term!r}"]
    for name, s in stats.items():
        lines.append(f"  {name:8} chunks={s['chunks']:4d}  docs={s['docs']:3d}  docs with it in heading_path={s['docs_in_heading_path']}")
    s = stats.get("heading") or next(iter(stats.values()))
    for doc, n in s["per_doc"][:show]:
        lines.append(f"      {n:3d} chunk(s)  {doc}")
    if len(s["per_doc"]) > show:
        lines.append(f"      ... {len(s['per_doc']) - show} more docs (use --show N)")
    if not s["docs"]:
        lines.append("      (no chunk contains this term: an exact-term question on it cannot be answered from the index)")
    return "\n".join(lines)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(usage="python -m eval.term_stats [--term=T ...] [--show N] [--case] [-- TERM ...]")
    ap.add_argument("terms", nargs="*")
    ap.add_argument("--term", action="append", default=[], help="use --term=--flag for a term that starts with a dash")
    ap.add_argument("--show", type=int, default=8, help="docs to list (default 8)")
    ap.add_argument("--case", action="store_true", help="case-sensitive")
    ap.add_argument("--chunks-dir", default="data/chunks")
    a = ap.parse_args(argv)
    terms = a.terms + a.term
    if not terms:
        ap.error("give at least one term")
    chunks = load_chunks(a.chunks_dir)
    for t in terms:
        print(report(t, term_stats(t, chunks, a.case), a.show))


if __name__ == "__main__":
    main()
