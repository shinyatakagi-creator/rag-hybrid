# Corpus pin

- Source: https://github.com/kubernetes/website (CC BY 4.0)
- Commit SHA: `6c42e266fcc1f0e0edd4805baea904e1b3cbaf9c` (main tip, 2026-10-22T23:07:34Z)
- Local checkout: `data/k8s-src/` (shallow, sparse); `data/k8s` is a symlink to `data/k8s-src/content/en`
- Sparse paths: `content/en/docs/{concepts,tasks,reference}` plus `content/en/examples` and `content/en/includes` (added after scoping; used only to resolve `code_sample` / `include`, never indexed). HEAD SHA verified unchanged (`6c42e266...`) after adding them.
- Chosen scope: **B**, 511 markdown pages (the 1,606 in the three folders minus the excluded directories below)

## Included (under `content/en/docs/`)
- `concepts/`: 187 pages
- `tasks/`: 221 pages
- `reference/`: 103 pages, all subdirectories except the excluded ones

## Excluded (generated or stub-heavy; guide allows skipping when count > ~500)
- `reference/kubernetes-api/` (162)
- `reference/glossary/` (163)
- `reference/command-line-tools-reference/` (497)
- `reference/setup-tools/` (153)
- `reference/kubectl/` (120)

## Counts (from the Phase 1 run, eval/results/phase1_stats.txt)
- 511 pages loaded; 489 produce chunks; the other 22 are section `_index.md` pages with front matter only (no body text).
- Chunks: 4,211 fixed, 4,824 heading.

`doc_id` = page path relative to `content/en/docs/`, without extension.
The golden set depends on this staying fixed; do not update the checkout.
