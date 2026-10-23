"""The list of indexed pages and lookups between doc_id, URL and title.

    python -m eval.docids --write                       # (re)generate eval/doc_ids.tsv from the corpus + chunk files
    python -m eval.docids --url https://kubernetes.io/docs/concepts/workloads/pods/
    python -m eval.docids --title "id limits"           # case-insensitive substring of the page TITLE (not doc_id or text)
    python -m eval.docids --id concepts/policy/pid-limiting

`eval/doc_ids.tsv` is the list of the 502 indexed pages (committed, so you can open it in any editor or spreadsheet):
doc_id, url, title, chunks_fixed, chunks_heading. A page with 0 chunks is in the corpus but has no body text (a bare
section index), so retrieval can never return it: do not use it as an expected_doc_id.
"""
import argparse
import csv
import json
from pathlib import Path

from ingest.loaders import load_corpus

LIST_PATH = "eval/doc_ids.tsv"
FIELDS = ["doc_id", "url", "title", "chunks_fixed", "chunks_heading"]
HOSTS = ("https://kubernetes.io", "http://kubernetes.io", "https://www.kubernetes.io")


def build_rows(corpus: str = "data/k8s", chunks_dir: str = "data/chunks") -> list[dict]:
    counts = {}
    for name in ("fixed", "heading"):
        for line in open(Path(chunks_dir) / f"{name}.jsonl", encoding="utf8"):
            d = json.loads(line)["doc_id"]
            counts.setdefault(d, {"fixed": 0, "heading": 0})[name] += 1
    rows = []
    for d in load_corpus(Path(corpus), raw=True):
        c = counts.get(d.doc_id, {"fixed": 0, "heading": 0})
        rows.append({"doc_id": d.doc_id, "url": d.url, "title": d.title, "chunks_fixed": c["fixed"], "chunks_heading": c["heading"]})
    return sorted(rows, key=lambda r: r["doc_id"])


def write_list(rows: list[dict], path: str = LIST_PATH) -> None:
    with open(path, "w", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read_list(path: str = LIST_PATH) -> list[dict]:
    with open(path, encoding="utf8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        r["chunks_fixed"], r["chunks_heading"] = int(r["chunks_fixed"]), int(r["chunks_heading"])
    return rows


def candidates_from_url(url: str) -> list[str]:
    """kubernetes.io/docs/<path>/ -> doc_id candidates. A leaf page is <path>; a section page is <path>/_index
    (both have URL <path>/), so both are tried."""
    u = url.strip().split("#")[0].split("?")[0]
    for h in HOSTS:
        if u.startswith(h):
            u = u[len(h):]
    if not u.startswith("/docs/"):
        return []
    path = u[len("/docs/"):].strip("/")
    return [path, f"{path}/_index"] if path else []


def lookup_url(url: str, rows: list[dict]) -> list[dict]:
    by_id = {r["doc_id"]: r for r in rows}
    return [by_id[c] for c in candidates_from_url(url) if c in by_id]


def find_title(text: str, rows: list[dict]) -> list[dict]:
    return [r for r in rows if text.lower() in r["title"].lower()]


def _show(r: dict) -> str:
    note = "" if r["chunks_heading"] and r["chunks_fixed"] else "   <-- NO CHUNKS: cannot be retrieved, do not use"
    return f"{r['doc_id']}\n    {r['url']}\n    title={r['title']!r} chunks fixed={r['chunks_fixed']} heading={r['chunks_heading']}{note}"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help=f"regenerate {LIST_PATH}")
    ap.add_argument("--url")
    ap.add_argument("--title")
    ap.add_argument("--id")
    a = ap.parse_args(argv)
    if a.write:
        rows = build_rows()
        write_list(rows)
        print(f"wrote {LIST_PATH}: {len(rows)} pages, {sum(1 for r in rows if not r['chunks_heading'])} without chunks")
        return
    rows = read_list()
    if a.url:
        hits = lookup_url(a.url, rows)
        print("\n".join(_show(r) for r in hits) if hits else f"not an indexed page: {a.url}\n  candidates tried: {candidates_from_url(a.url) or 'none (not a /docs/ URL)'}\n"
              "  (excluded folder, headless partial, or outside concepts/tasks/reference)")
    elif a.title:
        hits = find_title(a.title, rows)
        print("\n".join(_show(r) for r in hits[:30]) or "no title matches")
        if len(hits) > 30:
            print(f"... {len(hits) - 30} more")
    elif a.id:
        hit = [r for r in rows if r["doc_id"] == a.id]
        print(_show(hit[0]) if hit else f"{a.id!r} is not an indexed doc_id")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
