"""How much of a question's vocabulary is already on the page it should find? No API calls, no Elasticsearch.

    python -m eval.overlap_check --question "How can I stop one tenant from using all the process slots?" \\
        --doc-id concepts/policy/pid-limiting [--doc-id other/page] [--type conceptual|mixed|exact_term] [--exact-term TERM]

Reads the indexed chunk file (data/chunks/heading.jsonl): the page text is its title plus all its chunk text, and the
document frequencies (what counts as a "rare" term) come from the 477 pages that have chunks. For each --doc-id it prints
  * the overlap ratio: share of the question's content terms (stemmed, stopwords removed) that occur on the page,
  * the shared rare terms: shared terms found on under 20% of pages, which are the ones BM25 latches onto,
  * any copied run of 4 consecutive words,
  * whether a draft of that --type would be flagged (thresholds: eval/overlap.py), and
  * the chunks of the page that overlap most.
For a mixed question the exact term(s) are taken out first (given with --exact-term, or detected: flags, camelCase,
snake_case, hyphenated names, anything in backticks), because sharing the exact term is the point of that type.
"""
import argparse
import sys

from eval.overlap import (
    FLAG_DISTINCTIVE, FLAG_RATIO, content_terms, detect_exact_terms, doc_frequency, flags_for, page_texts, question_metrics, shared_terms,
)

RARE_DF = 0.2  # same cutoff as eval.overlap.distinctive_shared
TOP_CHUNKS = 3


def analyze(question: str, doc_id: str, texts: dict[str, str], chunks: dict[str, list[dict]], df, n_docs: int,
            typ: str = "conceptual", exact_terms: list[str] | None = None) -> dict:
    if doc_id not in texts:
        raise KeyError(f"{doc_id!r} is not an indexed page with chunks (look it up with: python -m eval.docids --title ... / --url ...)")
    terms = exact_terms if exact_terms is not None else (detect_exact_terms(question) if typ == "mixed" else [])
    q = question
    for t in terms:
        q = q.replace(t, " ")
    text = texts[doc_id]
    m = question_metrics(question, terms, text, df, n_docs)
    q_terms, shared = content_terms(q), shared_terms(q, text)
    shared_df = sorted(((t, df[t] / n_docs) for t in shared), key=lambda x: (x[1], x[0]))
    per_chunk = []
    for c in chunks[doc_id]:
        cm = question_metrics(question, terms, c["heading_path"] + "\n" + c["content"], df, n_docs)
        per_chunk.append({"heading_path": c["heading_path"], "token_count": c["token_count"], **cm})
    per_chunk.sort(key=lambda r: (-r["overlap_ratio"], -len(r["distinctive_shared"])))
    return {
        "doc_id": doc_id, "title": texts[doc_id].split("\n", 1)[0], "chunks": len(chunks[doc_id]), "type": typ, "exact_terms": terms,
        "question_terms": len(q_terms), "terms_on_page": len(shared), "terms_not_on_page": sorted(q_terms - shared),
        "shared_with_df": shared_df, "metrics": m, "flags": flags_for(m, typ), "top_chunks": per_chunk[:TOP_CHUNKS],
    }


def format_report(a: dict) -> str:
    m = a["metrics"]
    thr = FLAG_RATIO.get(a["type"])
    lines = [f"page {a['doc_id']}  ({a['title']!r}, {a['chunks']} chunks)"]
    if a["exact_terms"]:
        lines.append(f"  exact term(s) taken out of the question first: {a['exact_terms']}")
    lines.append(f"  overlap ratio        {m['overlap_ratio']:.2f}  ({a['terms_on_page']} of {a['question_terms']} question terms occur on the page)"
                 + (f"   [flag threshold for {a['type']}: {thr}]" if thr else f"   [{a['type']}: not flagged by design]"))
    shared = ", ".join(f"{t} ({p:.0%})" for t, p in a["shared_with_df"]) or "none"
    lines.append(f"  shared terms         {shared}   (percent = share of pages containing the term)")
    lines.append(f"  shared RARE terms    {', '.join(m['distinctive_shared']) or 'none'}   (under {RARE_DF:.0%} of pages; {FLAG_DISTINCTIVE}+ is flagged)")
    lines.append(f"  copied 4-word runs   {' | '.join(m['copied_phrases']) or 'none'}")
    if a["terms_not_on_page"]:
        lines.append(f"  question terms NOT on the page: {', '.join(a['terms_not_on_page'])}")
    lines.append(f"  verdict ({a['type']}): " + ("OK, no flags" if not a["flags"] else "FLAGGED: " + "; ".join(a["flags"]) if thr else "n/a"))
    lines.append("  chunks of this page that overlap most:")
    for r in a["top_chunks"]:
        lines.append(f"    {r['overlap_ratio']:.2f}  rare={len(r['distinctive_shared'])}  {r['heading_path'][-70:]}  ({r['token_count']} tok)")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="overlap of a question with the page(s) it should find; no API calls")
    ap.add_argument("--question", required=True)
    ap.add_argument("--doc-id", action="append", required=True, help="repeatable")
    ap.add_argument("--type", choices=["conceptual", "mixed", "exact_term"], default="conceptual")
    ap.add_argument("--exact-term", action="append", default=None, help="repeatable; for a mixed question (default: detected)")
    ap.add_argument("--chunks", default="data/chunks/heading.jsonl")
    a = ap.parse_args(argv)
    texts, chunks = page_texts(a.chunks)
    df, n = doc_frequency(list(texts.values())), len(texts)
    status = 0
    print(f"question: {a.question!r}   type: {a.type}   (document frequencies over {n} pages)\n")
    for doc in a.doc_id:
        try:
            print(format_report(analyze(a.question, doc, texts, chunks, df, n, a.type, a.exact_term)) + "\n")
        except KeyError as e:
            print(f"ERROR: {e.args[0]}\n")
            status = 2
    return status


if __name__ == "__main__":
    sys.exit(main())
