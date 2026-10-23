# Clean-clone reproducibility check (2026-10-24)

A fresh `git clone` of the repository (committed HEAD `8cc601c`) in a temp directory named `rag-hybrid`, only `.env` copied in (with `ES_INDEX=rag-docs-clean`), then `docs/SETUP.md` followed step by step:
venv + `pip install -r requirements.txt` (12 s) -> `scripts/fetch_corpus.sh` (pinned SHA verified, 502 pages / 477 with chunks) -> `docker compose up -d es` (reused the running Elasticsearch) ->
`ingest.run` (4,072 + 4,527 chunks) -> `ingest.index` (**paid**) -> `eval.retrieval_eval` -> `pytest` (312 passed) -> `docker compose build api` (builds from the clean tree).
The existing `rag-docs` index was not touched (8,599 docs before and after). `rag-docs-clean` and the clone were deleted afterwards. No `/ask` call was made; the API container was not recreated.

## Cost (API-reported usage)
- Corpus embedding: 86 calls, 2,670,798 tokens = **$0.0534** (estimate 2,670,798 tokens = $0.0534, +0.00%), 8,577 unique texts.
- Baseline eval query embeddings: 1 call, 691 tokens = $0.0000138.

## Result against `retrieval_baseline.json` (heading/hybrid is one of the six rows)
| row | baseline R@5 / R@10 / MRR | clean clone R@5 / R@10 / MRR | R@10 inside baseline 95% CI | MRR inside baseline 95% CI | first ranks that moved (of 26) |
|---|---|---|---|---|---|
| fixed/bm25 | 0.577 / 0.615 / 0.554 | 0.577 / 0.615 / 0.554 | yes | yes | 0 |
| fixed/dense | 0.821 / 0.865 / 0.654 | 0.821 / 0.865 / 0.654 | yes | yes | 0 |
| fixed/hybrid | 0.731 / 0.788 / 0.601 | 0.731 / 0.788 / 0.600 | yes | yes | 1 (c006: 6 -> 7) |
| heading/bm25 | 0.635 / 0.673 / 0.524 | 0.635 / 0.673 / 0.524 | yes | yes | 0 |
| heading/dense | 0.769 / 0.878 / 0.630 | 0.769 / 0.878 / 0.630 | yes | yes | 0 |
| heading/hybrid | 0.788 / 0.827 / 0.640 | 0.788 / 0.827 / 0.640 | yes | yes | 0 |

- **BM25 rows:** every overall and by-type number is identical. Three non-metric fields differ and are tie-breaking only: for fixed/bm25 e004 and e006 the 200-chunk window contains a different member among 6 (resp. 9) chunks with exactly the same score at the window edge (distinct docs 82 vs 81, 38 vs 37); for heading/bm25 c005 chunks 3-5 of the top 5 are different chunks with the identical score 24.902155 (nine chunks are tied at that score). Elasticsearch breaks equal-score ties by internal document id, which follows indexing order.
- **Dense / hybrid rows:** one per-question first rank moved in 104 (fixed/hybrid c006, 6 -> 7), which changes fixed/hybrid conceptual MRR from 0.129 to 0.126 and nothing else at the printed precision. Cause: the new query vectors are not all bit-identical to the cached ones (21 of 26 identical; max cosine distance 1.3e-5, max component difference 4.5e-4), and the chunk vectors were re-embedded as well.
- The golden file hash matched (`golden_sha256` equal).

## Git status in the clone after the run
Tracked files modified by the run: `eval/results/embed_run.json`, `eval/results/mapping.json` (both record the run; documented in SETUP.md). Untracked: `eval/results/retrieval_repro.{json,md}` and my own `ingest_run.log`. Ignored and not tracked: `.env`, `.venv/`, `data/` (corpus, chunks, embedding cache, query cache), `.pytest_cache/`. Tracked files under `data/`: 0; `.env` tracked: no.

## Steps that needed a fix
None needed a manual workaround during the run. Four documentation/script problems were found while preparing it and fixed beforehand or afterwards (see NOTES.md): the project-name trap (fixed `name:` and configurable host ports), the `ingest.index` prompt in non-interactive use (`--yes` documented), the baseline output path (`--out-json/--out-md` so the committed baseline is not overwritten), and the two tracked result files that steps 6-7 rewrite (documented with the restore command). The "BM25 rows should match exactly" sentence in SETUP.md was refined to what was observed.
