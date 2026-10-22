"""python -m ingest.run --corpus-dir data/k8s --chunker both

--corpus-dir is the dir holding docs/, examples/ and includes/ (data/k8s -> k8s-src/content/en).
"""
import argparse
import json
import re
import statistics
from collections import Counter
from pathlib import Path

from .chunkers import CHUNKERS, MAX_TOKENS, embed_text, ntok
from .loaders import _FENCE_SPLIT, Cleaner, load_corpus

LEFTOVER = re.compile(r"\{\{|\}\}|\{%|%\}|<!--|-->")


def outside_fences(text: str) -> str:
    return "".join(_FENCE_SPLIT.split(text)[::2])


def table_without_header(content: str) -> bool:
    lines = [l for l in content.split("\n") if l.strip()]
    return len(lines) > 1 and lines[0].lstrip().startswith("|") and not re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[1])


def unbalanced_fence(content: str) -> bool:
    return sum(1 for l in content.split("\n") if l.lstrip().startswith(("```", "~~~"))) % 2 == 1


def chunker_stats(chunks: list[dict]) -> dict:
    t = sorted(c["token_count"] for c in chunks)
    return {
        "chunks": len(chunks),
        "docs": len({c["doc_id"] for c in chunks}),
        "tokens_min": t[0],
        "tokens_median": statistics.median(t),
        "tokens_max": t[-1],
        "tokens_total": sum(t),
        "over_800": sum(x > MAX_TOKENS for x in t),
        "under_100": sum(x < 100 for x in t),
        "unbalanced_fence": sum(unbalanced_fence(c["content"]) for c in chunks),
        "table_without_header": sum(table_without_header(c["content"]) for c in chunks),
        "title_only_heading_path": sum(" > " not in c["heading_path"] for c in chunks),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-dir", default="data/k8s")
    ap.add_argument("--chunker", choices=["fixed", "heading", "both"], default="both")
    ap.add_argument("--out", default="data/chunks")
    ap.add_argument("--stats-out", default="eval/results/chunk_stats.json")
    a = ap.parse_args()

    cleaner = Cleaner(Path(a.corpus_dir))
    docs = load_corpus(Path(a.corpus_dir), cleaner)
    raw = load_corpus(Path(a.corpus_dir), cleaner, raw=True)
    stats = {
        "pages": len(docs),
        "corpus_tokens_raw": sum(ntok(d.text) for d in raw),
        "corpus_tokens_cleaned": sum(ntok(d.text) for d in docs),
        "unknown_shortcodes": dict(cleaner.unknown),
        "missing_refs": cleaner.missing,
    }
    print(f"pages={stats['pages']}  tokens raw={stats['corpus_tokens_raw']:,} cleaned={stats['corpus_tokens_cleaned']:,}")
    print(f"unknown shortcodes stripped: {stats['unknown_shortcodes']}  missing refs: {stats['missing_refs']}")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    names = ["fixed", "heading"] if a.chunker == "both" else [a.chunker]
    for name in names:
        chunks = [c for d in docs for c in CHUNKERS[name](d)]
        with open(out / f"{name}.jsonl", "w", encoding="utf8") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        s = stats[name] = chunker_stats(chunks)
        per_doc = Counter(c["doc_id"] for c in chunks)
        s["top_docs_by_chunks"] = per_doc.most_common(10)
        left = [c for c in chunks if LEFTOVER.search(outside_fences(embed_text(c)))]
        s["leftover_shortcode_chunks_outside_fences"] = len(left)
        s["leftover_examples"] = [(c["chunk_id"], LEFTOVER.search(outside_fences(embed_text(c))).group(), c["doc_id"]) for c in left[:5]]
        s["braces_inside_fences_(legit code)"] = sum(bool(LEFTOVER.search(c["content"])) for c in chunks) - len(left)
        print(f"\n[{name}] -> {out / (name + '.jsonl')}")
        print(json.dumps({k: v for k, v in s.items() if k not in ("top_docs_by_chunks", "leftover_examples")}, indent=1))
        if s["over_800"]:
            raise SystemExit(f"FAIL: {s['over_800']} {name} chunks exceed {MAX_TOKENS} tokens")

    Path(a.stats_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.stats_out).write_text(json.dumps(stats, indent=1, ensure_ascii=False))
    left_docs = sum(bool(LEFTOVER.search(outside_fences(d.text))) for d in docs)
    print(f"\ncleaned docs with leftover shortcode/comment markers outside fences: {left_docs}/{len(docs)}")


if __name__ == "__main__":
    main()
