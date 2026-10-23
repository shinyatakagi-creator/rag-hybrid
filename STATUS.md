# Status (2026-10-23, written for a context handoff)

The build guide (spec and handover rules) is `docs/BUILD_GUIDE.md`.

**Current phase: Phase 7, golden set (checkpoint 2).** Phases 0-6 are built and committed. No retrieval eval and no answer generation until the golden set is final. `NOTES.md` has every deviation from the guide; `eval/GOLDEN_README.md` explains the golden-set tools. Last commit: `8985644` (224 tests passed there).

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

## Current plan: 30-question golden set via a question kit for Gemini
**Owner decisions (2026-10-23):** target counts are **8 exact_term / 8 mixed / 10 conceptual / 4 unanswerable = 30** (`golden_check` `TARGETS` and `GOLDEN_README.md` updated). The Gemini route replaces the 38 model drafts; `eval/golden_drafts.*` stay committed as a record, no further review. The owner produces `eval/golden_owner.jsonl` from Gemini using the kit and verifies the pages himself. Checkpoint 3 (trial licence) waits until the retrieval eval.

**The kit (committed):** `eval/build_question_kit.py` (deterministic, seed 11, no API calls) generates `eval/question_kit.md`: A exact-term 12 candidates, B mixed 10 (each with a verbatim fact), C conceptual 12 passages, D unanswerable 4 (+2 off-topic). `extract_fact` now requires at least `MIN_FACT_WORDS` (6) words instead of rejecting letters-only sentences; the regenerated kit is byte-identical to the old one (the bug did not change this seed's picks), and the 13 kit tests pass. Handing the kit to Gemini is the owner's action.

## Next steps
1. You: produce `eval/golden_owner.jsonl`, check with `python -m eval.golden_check` and `python -m eval.overlap_check`; I merge and renumber to `eval/golden.jsonl` (`q001`...).
2. Then Phase 7: `eval/retrieval_eval.py` (exhausted-list rule from `eval/metrics.py`, pool sweep 50/100/200, six chunker x mode rows split by question type), `eval/answer_eval.py`, the checkpoint-4 sampler; checkpoint 3 (trial licence, native vs Python cross-check) happens at the retrieval eval; then Phase 8 (API, Docker, small query-embedding cache).
3. Checkpoint 4 (hand-label 25 verifier judgements) and checkpoint 5 (README results, CV bullet) come later.

## Spend so far: about $0.2895 of the $5 limit (no API calls since the drafting run)
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
