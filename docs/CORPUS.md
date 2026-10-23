# Corpus pin

- Source: https://github.com/kubernetes/website (CC BY 4.0)
- Commit SHA: `6c42e266fcc1f0e0edd4805baea904e1b3cbaf9c` (main tip, 2026-10-22T23:07:34Z)
- Local checkout: `data/k8s-src/` (shallow, sparse); `data/k8s` is a symlink to `data/k8s-src/content/en`
- Sparse paths: `content/en/docs/{concepts,tasks,reference}` plus `content/en/examples` and `content/en/includes` (added after scoping; used only to resolve `code_sample` / `include`, never indexed). HEAD SHA verified unchanged (`6c42e266...`) after adding them.
- Chosen scope: **B**, 502 indexed pages: the 1,606 markdown files in the three folders, minus the excluded directories below (511), minus the 9 headless include partials under `tasks/tools/included/` (`headless: true` / `render: never`, not public pages; excluded 2026-10-24).

## Included (under `content/en/docs/`)
- `concepts/`: 187 pages
- `tasks/`: 212 pages (221 minus the 9 headless partials)
- `reference/`: 103 pages, all subdirectories except the excluded ones

## Excluded (generated or stub-heavy; guide allows skipping when count > ~500)
- `reference/kubernetes-api/` (162)
- `reference/glossary/` (163)
- `reference/command-line-tools-reference/` (497)
- `reference/setup-tools/` (153)
- `reference/kubectl/` (120)

## Counts (from the Phase 1 run, eval/results/phase1_stats.txt)
- **502 pages** loaded; **477 produce chunks**; the other 25 are section `_index.md` pages with no body text (front matter only).
- Chunks (after stripping "What's next" navigation sections and the headless pages, and decoding HTML entities outside code): **4,072 fixed, 4,527 heading**. 281 "What's next" sections / 30,606 tokens are removed in the loader before chunking; 1,281 HTML entities are decoded in prose and 109 are left inside code (see NOTES.md). Earlier states: 4,211 / 4,824 (no rule), 4,103 / 4,544 (What's next stripped, 511 pages), 4,087 / 4,528 (502 pages, entities not yet decoded).
- Index `rag-docs`: **8,599 docs** (4,072 fixed + 4,527 heading) from 8,577 unique embedded texts. `eval/doc_ids.tsv` lists the same 502 pages (13 rows changed chunk counts, all in `reference/config-api`).
- Front-matter bug fixed on the same date: 4 `_index.md` pages whose closing `---` is the last bytes of the file used to keep their front matter as page text (junk chunks); they are now body-less like the others.

`doc_id` = page path relative to `content/en/docs/`, without extension.
The golden set depends on this staying fixed; do not update the checkout.
