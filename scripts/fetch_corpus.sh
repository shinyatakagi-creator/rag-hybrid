#!/usr/bin/env bash
# Fetch the pinned Kubernetes documentation corpus (kubernetes/website, CC BY 4.0) into data/k8s-src and link data/k8s to it.
#
#   scripts/fetch_corpus.sh [DEST]        DEST defaults to data/k8s-src; the link <parent of DEST>/k8s -> DEST/content/en is created
#
# Same scope as the original checkout: shallow (depth 1), blob-filtered, sparse paths content/en/docs/{concepts,tasks,reference} plus
# content/en/examples and content/en/includes (the last two are read only to resolve shortcodes, never indexed).
# Fails loudly if the checked-out commit is not the pinned one, or if the page count is not 502 loaded / 477 with chunks.
# Needs the project's Python environment active (the check uses the project's loader): see docs/SETUP.md.
set -euo pipefail

SHA="6c42e266fcc1f0e0edd4805baea904e1b3cbaf9c"
REPO="https://github.com/kubernetes/website.git"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DEST="${1:-data/k8s-src}"
PYTHON="${PYTHON:-python}"

die() { echo "ERROR: $*" >&2; exit 1; }

grep -q "$SHA" docs/CORPUS.md || die "docs/CORPUS.md does not mention the pinned SHA $SHA; the script and the corpus note disagree"
command -v git >/dev/null || die "git is required"
"$PYTHON" -c "import bs4, tiktoken, langchain_text_splitters" 2>/dev/null || die "the project's Python environment is not active (python cannot import bs4/tiktoken/langchain_text_splitters). Activate .venv and run: pip install -r requirements.txt"

if [ -d "$DEST/.git" ]; then
  echo "$DEST exists; checking it instead of cloning"
else
  [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ] && die "$DEST exists and is not a git checkout; refusing to touch it"
  mkdir -p "$DEST"
  git -C "$DEST" init -q
  git -C "$DEST" remote add origin "$REPO"
  git -C "$DEST" config core.sparseCheckout true
  git -C "$DEST" sparse-checkout init --cone
  git -C "$DEST" sparse-checkout set content/en/docs/concepts content/en/docs/tasks content/en/docs/reference content/en/examples content/en/includes
  echo "fetching $SHA (shallow, blob-filtered) ..."
  git -C "$DEST" fetch -q --depth 1 --filter=blob:none origin "$SHA"
  git -C "$DEST" checkout -q FETCH_HEAD
fi

GOT="$(git -C "$DEST" rev-parse HEAD)"
[ "$GOT" = "$SHA" ] || die "checked-out commit is $GOT, expected $SHA. Do not use this checkout: the golden set and every result depend on the pinned commit."
echo "commit OK: $GOT"

PARENT="$(dirname "$DEST")"
ln -sfn "$(basename "$DEST")/content/en" "$PARENT/k8s"
echo "linked $PARENT/k8s -> $(basename "$DEST")/content/en"

"$PYTHON" scripts/check_corpus.py --corpus-dir "$PARENT/k8s" || die "page count check failed (see above)"
echo "corpus ready: $PARENT/k8s (source: $REPO @ $SHA, CC BY 4.0)"
