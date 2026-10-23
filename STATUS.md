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

## Robustness, index cleanup, native RRF (2026-10-23)
- `eval/results/robustness_summary.{json,md}` (from saved results only, `eval/robustness_summary.py`): Recall@10 / MRR per row on exact_term, mixed, conceptual and bare_term, plus the worst slice (conceptual for every row); weighted-RRF hybrid rows are a separate sensitivity section.
- `rag-docs-hnsw` deleted (results and `mapping_hnsw.json` are saved). `rag-docs` untouched: 8,599 docs (4,072 fixed + 4,527 heading), effective bbq_hnsw, and a baseline rerun after the delete is identical.
- **Checkpoint 3 done.** Trial licence started by the owner (expires 2026-11-22). `eval/results/native_rrf_check.{json,md}` (`eval/native_rrf_check.py`): native `rrf` retriever (rank_constant 60, rank_window_size 200, same filters) vs Python RRF on 26 questions x 2 chunkers: first expected-doc rank identical in 52 of 52; top-10 chunk order identical in 48 of 52, the 4 differences are exact RRF score ties ordered differently (float32 vs exact fractions), one of which shifts the 10th distinct doc (m004 heading, 9 of 10 docs in common). The Python fusion is validated.

## Answer eval (run 2026-10-23, `eval/results/answer_eval.{json,md}`, review report `answer_eval_review.md`, logs `answer_eval_{generation,verification}.jsonl`)
Pre-registered configs `heading/hybrid` (dense weight 1) and `heading/dense`, 30 questions, context top 8 / max 2 per doc, Sonnet 5.5 answers, Haiku 5.5 claims-v2 verifier. Nothing was tuned after seeing results. Run cost **$0.7295** (spend guard; typical estimate was $0.85). The one verification failure (hybrid e007) was retried once with owner approval and succeeded (both attempts logged, NOTES.md); results below include it. 95% bootstrap CIs resample questions.
- **hybrid**: answer coverage 0.808 (0.65-0.96; 21 of 26 answered), false refusals 5, context coverage 0.808; strict faithfulness 0.962 (0.92-1.00) over 78 sentences, lenient 1.000, citation precision 0.917 (0.86-0.97); correct refusals 4 of 4, answered-unanswerable 0.
- **dense**: answer coverage 0.885 (0.73-1.00; 23 of 26), false refusals 3, context coverage 0.846; strict 0.961 (0.91-1.00) over 77 sentences, lenient 1.000, citation precision 0.951 (0.89-1.00); correct refusals 4 of 4, answered-unanswerable 0.
- Paired hybrid vs dense: both answered 20; only hybrid 1; only dense 3; both refused 2 (answerable). Where both were verified (n = 20) hybrid had a higher strict share in 2 questions, equal in 16, lower in 2. Intervals overlap heavily: no winner.
- Most false refusals follow retrieval misses (expected doc absent from the context). Faithfulness = support by the cited excerpts, not correctness against the references. The verifier is unvalidated until the checkpoint-4 hand labels. 11 of 165 cited pairs were not `yes`, each with an id (P01-P11) in `answer_eval_review.md`.

## Correctness check (run 2026-10-23; `eval/correctness_check.py`, `eval/results/correctness_check.{json,md}`, `correctness_review.md`, log `correctness_log.jsonl`; cost $0.0073)
Pre-registered: Haiku judges each answered answerable answer (hybrid 21, dense 23) against `reference_answer`: key facts covered (yes/partial/no) and contradicts reference (yes/no), structured and validated; the judge sees the question, reference and answer text only. It measures agreement with the references (written from the expected pages), not truth, and the judge is unvalidated.
- Results: hybrid 18 of 21 clean (covered yes and no contradiction), dense 18 of 23; 0 judged `no`; contradicts-reference flagged on 2 + 2 (hybrid m007, c007; dense m007, c007). 8 answers not clean in total plus 6 seeded random clean ones are in `correctness_review.md`, which has a "your mark" column (answer wrong / reference too narrow / judge wrong). m007 (dense) answers that hand additions survive a restart: possibly a case of "reference too narrow", for you to decide. **Your spot-check of about 10 rows is pending.**
- **Judge controls (pre-registered, built from heading/dense answers, definitions in `CONTROLS` in the module):** 3 swapped to an unrelated question (S1 e002 answer vs c010 question, S2 m001 vs c005, S3 e005 vs e004), 3 edited (A1 m002 inverted "disables" to "enables", A2 m003 "Cosign 2.0" to "1.0", A3 m006 "rejects" to "accepts and ignores"), 2 hand-written faithful rewordings (R1 e004, R2 e008). Result: **6 of 6 wrong controls caught** (key facts no or contradicts yes), **0 of 2 correct controls wrongly failed**, 0 control errors. n is tiny: it shows the judge is not blind to blatant errors, not that it is accurate on subtle ones.

## Checkpoint 4: hand labelling plan (sampler BUILT, labels NOT yet given; nothing is computed from labels until you finish)
- `python -m eval.checkpoint4 sample` (done; seed 30): all 11 cited (sentence, excerpt) pairs the Haiku verifier did not mark `yes` + 19 random `yes` pairs (out of 154), shuffled into L01..L30. `eval/checkpoint4/labelling_sheet.md` shows only the sentence and its cited excerpt text (what the verifier saw): no verdict, reason, claims, config, question id/type, page or heading. The pair-to-verdict key is in `eval/checkpoint4/key_do_not_open_until_labelled.json`: do not open it before labelling.
- You: write one label per row (`supported` / `partial` / `unsupported`, from that excerpt alone) in `eval/checkpoint4/my_labels.csv` (`id,label,note`).
- Only after all 30 are saved: `python -m eval.checkpoint4 score` (refuses on incomplete labels) writes `eval/checkpoint4/agreement.json`: exact agreement (verifier yes/partial/no vs supported/partial/unsupported), 3x3 confusion matrix (human rows, verifier columns), per-stratum agreement and a population-weighted agreement (the sample over-represents non-yes pairs), and the false-yes rate = share of the 19 verifier-`yes` pairs you did not label `supported` (also the stricter `unsupported`-only version) with an exact Clopper-Pearson 95% interval. `sample` refuses to overwrite a labels file that already has labels.

## Checkpoint 4 round 1 (done; scored 2026-10-23)
`eval/checkpoint4/my_labels.csv` (owner's labels, unmodified) and `agreement.json` are committed as the **first pass: first pass; labels not edited after unblinding; the disagreement review found apparent labelling inconsistencies (e.g. L25, L18, L08 near-verbatim but labelled unsupported; L06/L21 half-covered but labelled supported).** Numbers: exact agreement 11 of 30 (0.367); `yes` stratum 8 of 19, not-`yes` stratum 3 of 11; population-weighted 0.411; false-yes rate 11 of 19 = 0.579 (exact 95% CI 0.335-0.797), `unsupported`-only 6 of 19 = 0.316 (0.126-0.566). Do not quote these as the verifier's accuracy until round 2.

## Checkpoint 4 round 2 (sampler BUILT, labels NOT yet given; nothing is computed until you finish)
`python -m eval.checkpoint4_round2 sample` (done; seed 2026; no API calls): `eval/checkpoint4/round2/labelling_sheet.md` has 30 items M01..M30 in the round-1 format (sentence + cited excerpt only), the rubric at the top (split into claims; supported = every claim in the excerpt or directly implied, paraphrase counts; partial = some claims present, none contradicted; unsupported = the excerpt contradicts the sentence or the main claim is absent). Contents: 24 verifier-`yes` pairs not in round 1 + 6 controls from the verifier mutation set (3 known-wrong: M01 swapped citation, M06 changed number, M10 inverted claim, expected `unsupported`; 3 verbatim-correct: C02, C04, C05, expected `supported`), shuffled, nothing marks the controls. Key in `eval/checkpoint4/round2/key_do_not_open_until_labelled.json`.
- You: fill `eval/checkpoint4/round2/my_labels.csv` (`id,label,note`).
- **Pre-registered validity rule:** if you mislabel more than 1 of the 6 controls (2 or more), the round is INVALID for judging the verifier and is redone; `score` then reports the controls and stops.
- Only after all 30 are saved: `python -m eval.checkpoint4_round2 score` (refuses on incomplete labels) reports, in this order: control results; false-yes rate over the 24 yes pairs (not `supported`, and `unsupported`-only) with exact Clopper-Pearson 95% intervals; the distribution of your labels over the verifier's `yes` (agreement = share `supported`). Output: `eval/checkpoint4/round2/agreement.json`.

## Next steps
1. Spot-check about 10 rows of `correctness_review.md` (mark column; still pending: marks not yet received, so no reference correction for m007/c007 has been made).
2. Label round 2 (M01..M30); then I run `score`.
3. Phase 8: API, Docker, small query-embedding cache. Checkpoint 5: README results and CV bullet only after you have seen the saved eval outputs.

## Spend so far: about $0.2895 of the $5 limit (plus about $0.000015 for the baseline and bare-term query embeddings and $0.7295 for the answer eval, plus $0.0073 for the correctness check, so about $1.03 in total)
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
