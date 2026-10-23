"""python -m eval.golden_check eval/golden_owner.jsonl

Checks a golden-set file against the agreed format (see eval/GOLDEN_README.md) and against the list of indexed pages
(eval/doc_ids.tsv): known doc_ids that actually have chunks, at least 1 expected doc for answerable questions, none for
unanswerable ones, unique ids, no leftover REPLACE placeholders. Exits 1 when there are errors. More than 3 expected
docs is only a WARNING (exit stays 0); an optional non-empty "note" field on the line says why and silences it.

It also prints an overlap summary per question type (how much of each question's vocabulary is already on its expected
page(s); same numbers as `python -m eval.overlap_check`). `--json-out PATH` saves it for the README; `--no-overlap` skips it.
"""
import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

from eval.docids import LIST_PATH, read_list
from eval.overlap import FLAG_DISTINCTIVE, FLAG_RATIO, detect_exact_terms, doc_frequency, flags_for, page_texts, question_metrics

TYPES = ("exact_term", "conceptual", "mixed", "unanswerable")
TARGETS = {"exact_term": 10, "conceptual": 20, "mixed": 15, "unanswerable": 5}  # the 50-question plan
KEYS = {"id", "type", "question", "expected_doc_ids", "reference_answer", "answerable"}
OPTIONAL = {"note"}  # free text; a non-empty note on a question with more than 3 expected docs silences that warning
MAX_EXPECTED = 3


def check_line(obj, docs: dict[str, dict]) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one parsed line. Errors make the file invalid; warnings do not."""
    if not isinstance(obj, dict):
        return ["not a JSON object"], []
    errs, warns = [], []
    if not KEYS <= set(obj) or set(obj) - KEYS - OPTIONAL:
        return [f"keys must be {sorted(KEYS)} (plus optional {sorted(OPTIONAL)}); missing {sorted(KEYS - set(obj))}, unexpected {sorted(set(obj) - KEYS - OPTIONAL)}"], []
    if "note" in obj and not isinstance(obj["note"], str):
        errs.append("note must be a string")
    if not isinstance(obj["id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]+", obj["id"]):
        errs.append("id must be a non-empty string of letters, digits, '-' or '_'")
    if obj["type"] not in TYPES:
        errs.append(f"type {obj['type']!r} not in {TYPES}")
    if not isinstance(obj["question"], str) or len(obj["question"].strip()) < 8:
        errs.append("question must be a string of at least 8 characters")
    if not isinstance(obj["answerable"], bool):
        errs.append("answerable must be true or false")
    ids = obj["expected_doc_ids"]
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        return errs + ["expected_doc_ids must be a list of strings"], warns
    if len(set(ids)) != len(ids):
        errs.append("expected_doc_ids has duplicates")
    if obj["type"] == "unanswerable":
        if obj["answerable"] is not False:
            errs.append("an unanswerable question must have answerable=false")
        if ids:
            errs.append("an unanswerable question must have expected_doc_ids=[]")
    else:
        if obj["answerable"] is not True:
            errs.append("an answerable question must have answerable=true")
        if not ids:
            errs.append("an answerable question needs at least 1 expected doc")
        elif len(ids) > MAX_EXPECTED and not (isinstance(obj.get("note"), str) and obj["note"].strip()):
            warns.append(f"{len(ids)} expected docs (the plan is 1-{MAX_EXPECTED}): fine if the question really has that many answering pages; "
                         f"add a non-empty \"note\" field saying why to silence this warning")
        if not isinstance(obj["reference_answer"], str) or not obj["reference_answer"].strip():
            errs.append("reference_answer is required for an answerable question")
    for i in ids:
        d = docs.get(i)
        if d is None:
            errs.append(f"doc_id {i!r} is not an indexed page (see eval/doc_ids.tsv; python -m eval.docids --url/--title)")
        elif not (d["chunks_fixed"] and d["chunks_heading"]):
            errs.append(f"doc_id {i!r} has no chunks (body-less page), retrieval can never return it")
    if any("REPLACE" in str(v) for v in obj.values()):
        errs.append("still contains a REPLACE placeholder")
    return errs, warns


def check_file(path: str, docs_list: list[dict]) -> tuple[dict[int, list[str]], Counter, list[str], dict[int, list[str]]]:
    docs = {r["doc_id"]: r for r in docs_list}
    errors: dict[int, list[str]] = {}
    warnings: dict[int, list[str]] = {}
    counts: Counter = Counter()
    seen: Counter = Counter()
    for n, line in enumerate(Path(path).read_text(encoding="utf8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors[n] = [f"invalid JSON: {e}"]
            continue
        errs, warns = check_line(obj, docs)
        if warns:
            warnings[n] = warns
        if isinstance(obj, dict) and isinstance(obj.get("id"), str):
            seen[obj["id"]] += 1
            if seen[obj["id"]] > 1:
                errs.append(f"duplicate id {obj['id']!r}")
            if obj.get("type") in TYPES:
                counts[obj["type"]] += 1
        if errs:
            errors[n] = errs
    return errors, counts, [f"{t}: {counts[t]} (plan {TARGETS[t]})" for t in TYPES], warnings


def overlap_summary(path: str, texts: dict[str, str], df, n_docs: int) -> tuple[dict[str, dict], list[dict]]:
    """Overlap of each answerable question with its expected pages, then a summary per question type.

    Per question the worst case is used: the maximum over its expected docs (the page that would flatter BM25 most).
    For `mixed` questions the exact terms are detected and taken out first (as in the drafts); `exact_term` questions are
    expected to overlap and are reported but never flagged. Lines that do not parse or name an unknown doc are skipped."""
    rows = []
    for line in Path(path).read_text(encoding="utf8").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or obj.get("type") not in TYPES or obj["type"] == "unanswerable":
            continue
        ids = obj.get("expected_doc_ids")
        if not isinstance(ids, list) or not ids or not all(i in texts for i in ids) or not isinstance(obj.get("question"), str):
            continue
        terms = detect_exact_terms(obj["question"]) if obj["type"] == "mixed" else []
        per_doc = {i: question_metrics(obj["question"], terms, texts[i], df, n_docs) for i in ids}
        worst = max(per_doc.values(), key=lambda m: (m["overlap_ratio"], len(m["distinctive_shared"])))
        rows.append({"id": obj.get("id"), "type": obj["type"], "overlap_ratio": worst["overlap_ratio"],
                     "rare_terms": max(len(m["distinctive_shared"]) for m in per_doc.values()),
                     "copied_phrase": any(m["copied_phrases"] for m in per_doc.values()),
                     "flagged": any(flags_for(m, obj["type"]) for m in per_doc.values()), "exact_terms": terms,
                     "worst_doc": max(per_doc, key=lambda i: per_doc[i]["overlap_ratio"])})
    summary = {}
    for t in TYPES:
        rs = [r for r in rows if r["type"] == t]
        if not rs:
            continue
        ratios = [r["overlap_ratio"] for r in rs]
        summary[t] = {"n": len(rs), "ratio_median": statistics.median(ratios), "ratio_mean": round(statistics.mean(ratios), 2),
                      "ratio_min": min(ratios), "ratio_max": max(ratios), "rare_terms_mean": round(statistics.mean(r["rare_terms"] for r in rs), 1),
                      "copied_phrase": sum(r["copied_phrase"] for r in rs), "flagged": sum(r["flagged"] for r in rs) if t in FLAG_RATIO else None}
    return summary, rows


def format_overlap(summary: dict[str, dict]) -> str:
    out = ["overlap of each answerable question with its expected page(s); per question the worst case over its expected docs",
           f"  {'type':12} {'n':>3}  {'ratio median / mean / min / max':32} {'rare terms (mean)':>18} {'copied 4-gram':>14} {'flagged':>12}"]
    for t, s in summary.items():
        flagged = f"{s['flagged']} ({s['flagged'] / s['n']:.0%})" if s["flagged"] is not None else "n/a (by design)"
        out.append(f"  {t:12} {s['n']:3d}  {s['ratio_median']:.2f} / {s['ratio_mean']:.2f} / {s['ratio_min']:.2f} / {s['ratio_max']:.2f}".ljust(55)
                   + f" {s['rare_terms_mean']:18.1f} {s['copied_phrase']:14d} {flagged:>12}")
    out.append(f"  ratio = share of the question's content terms found on the page; rare = shared terms on under 20% of pages; flag rule: ratio >= "
               f"{FLAG_RATIO['conceptual']} (conceptual) / {FLAG_RATIO['mixed']} (mixed), {FLAG_DISTINCTIVE}+ rare terms, or a copied 4-word run")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--doc-list", default=LIST_PATH)
    ap.add_argument("--chunks", default="data/chunks/heading.jsonl", help="indexed chunks, the source of page text for the overlap summary")
    ap.add_argument("--no-overlap", action="store_true", help="skip the overlap summary")
    ap.add_argument("--json-out", help="also save the per-type summary and per-question numbers here (use for README figures)")
    a = ap.parse_args(argv)
    if not Path(a.path).exists():
        print(f"{a.path} does not exist yet")
        return 1
    errors, counts, summary, warnings = check_file(a.path, read_list(a.doc_list))
    for n, errs in errors.items():
        for e in errs:
            print(f"line {n}: ERROR {e}")
    for n, warns in warnings.items():
        for w in warns:
            print(f"line {n}: warning: {w}")
    status = "OK" if not errors else f"{sum(len(v) for v in errors.values())} error(s) on {len(errors)} line(s)"
    print(f"{status}, {sum(len(v) for v in warnings.values())} warning(s) | " + " | ".join(summary))
    if not a.no_overlap:
        if not Path(a.chunks).exists():
            print(f"\n(overlap summary skipped: {a.chunks} not found)")
        else:
            texts, _ = page_texts(a.chunks)
            ov, rows = overlap_summary(a.path, texts, doc_frequency(list(texts.values())), len(texts))
            print("\n" + (format_overlap(ov) if ov else "overlap summary: no answerable question with known expected docs yet"))
            if a.json_out:
                Path(a.json_out).write_text(json.dumps({"source": a.path, "pages": len(texts), "by_type": ov, "questions": rows}, indent=1))
                print(f"saved {a.json_out}")
    return 1 if errors else 0  # warnings never fail the check


if __name__ == "__main__":
    sys.exit(main())
