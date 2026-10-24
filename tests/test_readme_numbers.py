"""README.md numbers must trace to docs/numbers_manifest.json (no API calls, no ES).

scripts/make_readme_tables.py records, for every number it writes, the exact character span in
README.md plus its source. Here every digit of the README must lie inside such a span, and the text
at each span must still equal the recorded value, so a hand-typed or hand-edited digit fails.
README_PATH can point the check at another file (used to demonstrate the failure on a copy).
"""
import importlib.util
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = Path(os.environ.get("README_PATH", ROOT / "README.md"))
MANIFEST = ROOT / "docs" / "numbers_manifest.json"

# Digits that are not numbers from this project's results. Everything else must be in the manifest.
ALLOW = [
    r"\]\([^)]*\)",  # markdown link targets, e.g. (docs/SETUP.md)
    r"https?://[^\s)]+",  # URLs
    r"(?:Recall|R)@\d+",  # metric names: Recall@5, Recall@10, R@10
    r"(?i:bm25)",  # the algorithm's name, also in row labels like fixed/bm25
    r"float32",  # a data type name
    r"95%",  # the confidence level of every interval
]


def check(text, manifest):
    """Return a list of problems; empty means every digit is covered by a matching manifest span."""
    problems = []
    spans = sorted((o["start"], o["end"], o["text"], o["source"]) for o in manifest["occurrences"])
    for start, end, value, _ in spans:
        if text[start:end] != value:
            problems.append(f"span {start}-{end} should read {value!r} but reads {text[start:end]!r}")
    allowed = [False] * len(text)
    for pat in ALLOW:
        for m in re.finditer(pat, text):
            for i in range(m.start(), m.end()):
                allowed[i] = True
    for start, end, value, _ in spans:
        if text[start:end] == value:
            for i in range(start, end):
                allowed[i] = True
    for m in re.finditer(r"\d+", text):
        if not all(allowed[i] for i in range(m.start(), m.end())):
            line = text.count("\n", 0, m.start()) + 1
            ctx = text[max(0, m.start() - 25):m.end() + 15].replace("\n", " ")
            problems.append(f"line {line}: number {m.group()!r} is not in the manifest (...{ctx}...)")
    return problems


def test_every_readme_digit_is_in_the_manifest():
    manifest = json.loads(MANIFEST.read_text())
    problems = check(README.read_text(), manifest)
    assert not problems, "\n" + "\n".join(problems[:15])


def test_audit_is_generated_from_the_manifest():
    spec = importlib.util.spec_from_file_location("make_readme_tables", ROOT / "scripts" / "make_readme_tables.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    manifest = json.loads(MANIFEST.read_text())
    assert (ROOT / "docs" / "NUMBERS_AUDIT.md").read_text() == mod.audit_md(manifest)


def test_check_catches_a_changed_number_and_a_typed_digit():
    manifest = json.loads(MANIFEST.read_text())
    text = (ROOT / "README.md").read_text()
    assert check(text, manifest) == []
    changed = text.replace("0.827", "0.828", 1)  # same length, so every other span still lines up
    assert any("0.827" in p for p in check(changed, manifest))
    typed = text.replace("Elasticsearch BM25 and kNN", "Elasticsearch 7 BM25 and kNN", 1)
    assert check(typed, manifest)
