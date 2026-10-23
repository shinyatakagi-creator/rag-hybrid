"""python -m eval.golden_check eval/golden_owner.jsonl

Checks a golden-set file against the agreed format (see eval/GOLDEN_README.md) and against the list of indexed pages
(eval/doc_ids.tsv): known doc_ids that actually have chunks, 1-3 expected docs for answerable questions, none for
unanswerable ones, unique ids, no leftover REPLACE placeholders. Exits 1 when there are errors.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from eval.docids import LIST_PATH, read_list

TYPES = ("exact_term", "conceptual", "mixed", "unanswerable")
TARGETS = {"exact_term": 10, "conceptual": 20, "mixed": 15, "unanswerable": 5}  # the 50-question plan
KEYS = {"id", "type", "question", "expected_doc_ids", "reference_answer", "answerable"}


def check_line(obj, docs: dict[str, dict]) -> list[str]:
    if not isinstance(obj, dict):
        return ["not a JSON object"]
    errs = []
    if set(obj) != KEYS:
        return [f"keys must be exactly {sorted(KEYS)}; missing {sorted(KEYS - set(obj))}, unexpected {sorted(set(obj) - KEYS)}"]
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
        return errs + ["expected_doc_ids must be a list of strings"]
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
        if not 1 <= len(ids) <= 3:
            errs.append(f"expected_doc_ids needs 1-3 docs, has {len(ids)}")
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
    return errs


def check_file(path: str, docs_list: list[dict]) -> tuple[dict[int, list[str]], Counter, list[str]]:
    docs = {r["doc_id"]: r for r in docs_list}
    errors: dict[int, list[str]] = {}
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
        errs = check_line(obj, docs)
        if isinstance(obj, dict) and isinstance(obj.get("id"), str):
            seen[obj["id"]] += 1
            if seen[obj["id"]] > 1:
                errs.append(f"duplicate id {obj['id']!r}")
            if obj.get("type") in TYPES:
                counts[obj["type"]] += 1
        if errs:
            errors[n] = errs
    return errors, counts, [f"{t}: {counts[t]} (plan {TARGETS[t]})" for t in TYPES]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--doc-list", default=LIST_PATH)
    a = ap.parse_args(argv)
    if not Path(a.path).exists():
        print(f"{a.path} does not exist yet")
        return 1
    errors, counts, summary = check_file(a.path, read_list(a.doc_list))
    for n, errs in errors.items():
        for e in errs:
            print(f"line {n}: {e}")
    print(("OK" if not errors else f"{sum(len(v) for v in errors.values())} problem(s) on {len(errors)} line(s)") + " | " + " | ".join(summary))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
