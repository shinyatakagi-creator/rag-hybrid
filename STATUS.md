# Status (2026-10-23, written for a context handoff)

The build guide (spec and handover rules) is `docs/BUILD_GUIDE.md`.

**Current phase: Phase 7, baseline retrieval eval done; answer eval next. The golden set is FINAL and frozen (checkpoint 2 done).** Phases 0-6 are built and committed. `NOTES.md` has every deviation from the guide; `eval/GOLDEN_README.md` explains the golden-set tools. Last commit: `8985644` (224 tests passed there).

## Phases done

| Phase | Commit(s) | One line |
|---|---|---|
| 0 Setup | `b9d3d05` | ES 9.5.5, 1 GB heap, Kibana under `--profile debug`, pinned deps |
| 1 Chunking | `14655bf`, `3959f71`, `5eb9cf4`, `3ca1f19`, `6272ace` | 502 pages (477 with chunks); "What's next" sections stripped; headless partials excluded; HTML entities decoded outside code |
| 2 Index | `a23ab0b`, `2b21f82`, `f15a76c` | `rag-docs` = **8,599 docs** (4,072 fixed + 4,527 heading), counts match the chunk files, a rerun makes 0 embedding calls, effective `index_options` = `bbq_hnsw` |
| 3+4 Retrieval + RRF | `519a55a`, `cf704d8` | bm25 / dense / hybrid, own RRF (k=60), 200-chunk window, `distinct_docs` |
| 5 Generation | `cf704d8` | `claude-sonnet-5-5`, validated structured answers with citations; refusals work (3 test questions + the hard-refusal question) |
| 6 Verification | `bc853f1`, `57e1634` | `claude-haiku-5-5`, claims-based rubric v2 with the verdict derived in code; 25-pair dev set (not an accuracy figure); Sonnet cross-check agrees 25/25 |

## Done since the last STATUS update
- **Golden-set tooling** (`215b060`, `ce43ba8`): `eval/doc_ids.tsv` (the 502 pages, 25 have no chunks), `eval.docids` (URL / title / id lookups), `eval.term_stats`, `eval.golden_check` (format + known doc_ids; more than 3 expected docs is a warning silenced by an optional `note` field), template, `eval/GOLDEN_README.md`, `eval.draft_questions`.
- **HTML-entity fix** (`6272ace`, re-index `f15a76c`): 1,281 entities decoded in prose, 109 left inside code; also fixed indentation-aware fence detection and uppercase `<B>` tags. Re-embedded 721 texts for $0.0047.
- **Drafts** (`b529a30`): `eval/golden_drafts.md` / `.jsonl`: 22 conceptual + 16 mixed, 0 failed, 34 flagged, cost $0.1345. Flags are a signal: the model reduced word overlap with the source page but did not remove it (conceptual median overlap ratio 0.54). Known weaknesses: a few mixed drafts leak their own answer (d024, d031); some questions assume context. `source_doc` is only a suggestion for `expected_doc_ids`.
- **Overlap tools** (`8985644`): `python -m eval.overlap_check --question "..." --doc-id <id>` (no API calls) and a per-type overlap summary in `golden_check` (`--json-out eval/results/golden_overlap.json` for README figures). One implementation in `eval/overlap.py`; fixed a bug where an exact term's words were hidden from the rare-term count even when used in plain prose. Under the shared tools 33 of 38 drafts would be flagged (d002 flips); the drafts files were not regenerated.
- **Checkpoint-4 sampler design recorded, not built** (it needs real golden-set answers, so it comes after `answer_eval`): blind labelling (the labeller never sees the verifier's verdict, reason or claim statuses) and a stratified sample with every `partial` and `no` plus random `yes` to make 25.

## Golden set: final (checkpoint 2 done, 2026-10-23)
`eval/golden.jsonl` = 30 questions: **8 exact_term / 10 conceptual / 8 mixed / 4 unanswerable** (identical to `eval/golden_owner.jsonl`; ids are `e001`.. / `m001`.. / `c001`.. / `u001`.., not renumbered to `q001`..). `python -m eval.golden_check eval/golden.jsonl` passes (0 errors, 0 warnings); overlap figures for the README come from `eval/results/golden_overlap.json`. Every conceptual question has 0-1 shared rare terms and no copied 4-word run with its expected pages; ratio-only flags are accepted (conceptual 6 of 10, mixed 6 of 8 flagged). `eval/results/golden_page_check_lines.txt` holds the supporting lines found in each expected page. `eval/golden_owner.v1.jsonl` (the pre-rewrite file, kept untracked) and `eval/golden_drafts.*` (38 model drafts, not used) are records only.

**For the README (how the questions were made):** drafted with LLM help: Gemini wrote them from a verified corpus kit (`eval/question_kit.md`, built deterministically from the indexed pages with `term_stats` proof), then Claude Code reworded them against the overlap rules (`eval.overlap_check`, page text only, no retrieval output). The owner approved the final wording, and the expected pages were checked against page text (not retrieval results) and approved by the owner. The 4 unanswerable questions are confirmed absent: their key strings appear in 0 indexed chunks for both chunkers. Overlap is a lexical proxy, not a guarantee that a question is hard.

**Open item for the retrieval eval:** 4 questions list 2-3 expected pages (e007, c002, c005 have 2, c008 has 3); recall counts a hit on any expected page.

## Retrieval baseline (done 2026-10-23, `eval/results/retrieval_baseline.{json,md}`)
`python -m eval.retrieval_eval --yes` (code `eval/retrieval_eval.py`, tests `tests/test_retrieval_eval.py`): 6 rows (bm25 / dense / hybrid Python RRF k=60 x fixed / heading), current settings (pool 200, kNN k=200, num_candidates 800, index_options as built), 26 answerable questions at doc level, no tuning. Run twice: results, paired comparison and settings identical (the second run made 0 API calls). Query embeddings cost about $0.0000138 (26 queries, 691 tokens, 1 call). The golden set is frozen: no edits after seeing these results unless a genuine error is found, then with a NOTES.md entry and a full rerun.

Headline (read the intervals, n = 26): overall Recall@10 fixed bm25/dense/hybrid 0.615 / 0.865 / 0.788, heading 0.673 / 0.878 / 0.827; exact_term and mixed are near ceiling for every row; the difference is conceptual (n = 10), where bm25 is near 0 and dense beats hybrid (hybrid recall@10 0.45 fixed / 0.55 heading vs dense 0.65 / 0.68). Hybrid does not beat dense overall on this set. Full tables and per-question ranks are in the `.md`. No README claim yet (checkpoint 5).

## Sensitivity analyses (2026-10-23; reported as sensitivity, not tuning: there is no held-out set; the baseline above stays the headline)
Code `eval/sensitivity.py` (`bare-term`, `rrf-weights`, `index-options`), `eval/failure_analysis.py`; each result has its own file with settings in `eval/results/`. The golden set was not changed.
- **Bare-term diagnostic** (`bare_term.json/.md`; the exact term alone as the query for the 16 exact_term + mixed questions, 16 queries, 81 tokens, about $0.0000016): bm25 and hybrid hold Recall@10 at 0.94-1.00 (heading/bm25 and heading/hybrid 1.000), dense falls to 0.66 (fixed) / 0.72 (heading); MRR is lower for every row than with the full question (bm25 0.65 / 0.62, hybrid 0.49 / 0.61, dense 0.33 / 0.34). BM25 lists are exhausted for 9 of 16 queries (rare identifiers) yet still contain the expected doc every time.
- **Weighted RRF** (`rrf_weights.json/.md`; dense weight 1 / 1.5 / 2, bm25 weight 1; weight 1 reproduces the baseline hybrid exactly): all weights reported, none chosen. Overall hybrid Recall@10 0.788 / 0.821 / 0.821 (fixed) and 0.827 / 0.865 / 0.865 (heading); the movement is in conceptual questions; intervals overlap heavily at n = 26.
- **index_options** (`index_options.json/.md`; `rag-docs-hnsw` = explicit hnsw m16 / ef_construction 100, built from the cache with 0 embedding calls, mapping in `mapping_hnsw.json`; **kept for now**, delete it with `curl -X DELETE localhost:9200/rag-docs-hnsw` when no longer needed): dense and hybrid rows are identical to bbq_hnsw (top-10 chunk overlap 1.000 for dense, 0.992 / 1.000 for hybrid; one question's first-rank changes, fixed hybrid).
- **Failure analysis** (`failure_analysis.md`): c009, c010, c002 are hard conceptual questions whose answer is one sentence inside a longer section and whose wording avoids the sentence's key nouns; not golden-set errors.

## Next steps
1. `eval/answer_eval.py`, then the checkpoint-4 sampler (blind labelling, stratified: every `partial` and `no` plus random `yes` to make 25).
2. Native-RRF cross-check only if you want it (checkpoint 3: you start the trial licence); the pool sweep 50/100/200 has not been run.
3. Phase 8: API, Docker, small query-embedding cache. Checkpoint 5: README results and CV bullet only after you have seen the saved eval outputs.

## Spend so far: about $0.2895 of the $5 limit (plus about $0.000015 for the 26 baseline and 16 bare-term query embeddings)
| Item | Cost |
|---|---|
| Embeddings: corpus (2,750,672 tokens) + two re-embeds (66,058 and 234,612) + queries (~652, estimated) | $0.0610 |
| Answer generation, 4 questions (Sonnet 5.5) | $0.0477 |
| Verification and mutation tests, Haiku (v1 and v2) | $0.0058 |
| Sonnet 5.5 verifier cross-check | $0.0405 |
| Golden-set drafting, 38 calls (Sonnet 5.5) | $0.1345 |
| **Total** | **about $0.2895** |

Embedding and generation figures are API-reported usage; the ~652 query-embedding tokens are an estimate. `MAX_SPEND_USD` is enforced per run, not cumulatively.

## Resuming
- ES container `rag-hybrid-es-1`; `rag-docs` lives in a Docker volume (`docker compose up -d` if Docker was restarted).
- Local only, not in git: `.env` (both API keys), `data/` (corpus checkout, chunks, the 273+ MB embedding cache). Activate with `source .venv/bin/activate`.
- Run `pytest -q` first: expect all tests to pass.
