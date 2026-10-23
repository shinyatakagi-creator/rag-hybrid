"""python scripts/check_corpus.py [--corpus-dir data/k8s]

Loads the corpus with the project's own loader and chunkers (no file is written, no API call) and fails loudly if the page counts differ
from the pinned corpus (docs/CORPUS.md): 502 pages loaded, 477 of them with chunks. The chunk totals (4,072 fixed / 4,527 heading) are
checked too; a difference there is reported as a warning because it can come from a different library version, but it does change
retrieval numbers, so treat it as a reason to stop and compare.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingest.chunkers import CHUNKERS  # noqa: E402
from ingest.loaders import Cleaner, load_corpus  # noqa: E402

EXPECT_PAGES, EXPECT_CHUNKED = 502, 477
EXPECT_CHUNKS = {"fixed": 4072, "heading": 4527}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-dir", default="data/k8s")
    a = ap.parse_args()
    cleaner = Cleaner(Path(a.corpus_dir))
    docs = load_corpus(Path(a.corpus_dir), cleaner)
    ok = True
    print(f"pages loaded: {len(docs)} (expected {EXPECT_PAGES})")
    if len(docs) != EXPECT_PAGES:
        print(f"FAIL: expected {EXPECT_PAGES} pages, got {len(docs)}")
        ok = False
    for name in ("heading", "fixed"):
        chunks = [c for d in docs for c in CHUNKERS[name](d)]
        chunked = len({c["doc_id"] for c in chunks})
        print(f"[{name}] chunks: {len(chunks)} (recorded {EXPECT_CHUNKS[name]}); pages with chunks: {chunked} (expected {EXPECT_CHUNKED})")
        if chunked != EXPECT_CHUNKED:
            print(f"FAIL: expected {EXPECT_CHUNKED} pages with chunks, got {chunked}")
            ok = False
        if len(chunks) != EXPECT_CHUNKS[name]:
            print(f"WARNING: {name} chunk count differs from the recorded {EXPECT_CHUNKS[name]}; retrieval results will not reproduce exactly")
    print("corpus check: " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
