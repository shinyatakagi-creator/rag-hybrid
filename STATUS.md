# Status (2026-10-24, written for a context handoff)

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

## Current plan: a question kit for Gemini, target counts 8 / 10 / 8 / 4
Per the owner's latest message: build `eval/question_kit.md` (no API calls) as raw material for writing questions with Gemini, with target counts **8 / 10 / 8 / 4**. The message did not say which types the four numbers are. **Unconfirmed reading:** the kit's sections in order, A exact-term 8 (of 12 candidates), B mixed 10, C conceptual 8 (of 12 passages), D unanswerable 4 = 30 questions. `golden_check` and the README still assume the earlier 10 / 20 / 15 / 5 = 50 plan and need updating once the counts are confirmed.

**State of the kit (UNCOMMITTED, three untracked files):**
- `eval/build_question_kit.py`: deterministic generator (seed 11, no API calls). Builds A (12 rare terms in 1-5 docs: flags, fields, annotation keys, event reasons, error strings, each with a 3-6 line excerpt), B (10 more, each with a verbatim fact about the term), C (12 passages from different pages with each excerpt's 5 rarest tokens), D (4 real facts that live only in `command-line-tools-reference`, `reference/kubectl`, `kubernetes-api`, with `term_stats` proof the answer string appears in 0 indexed chunks, plus 2 off-topic questions). It checks its own constraints and fails the build if one does not hold.
- `eval/question_kit.md`: its generated output (A=12, B=10, C=12, D=4 + 2 off-topic). Excerpt blocks use 4-backtick fences so they cannot break the markdown.
- `tests/test_question_kit.py`: 13 tests, **12 pass, 1 fails** (`test_fact_must_mention_the_term_in_prose_and_say_something_about_it`).
- **Known bug found by that failing test, not yet fixed:** `extract_fact` rejects any sentence made only of letters, digits, spaces and ``.-/` ``-characters (a `re.fullmatch` meant to drop bare identifiers), so section B's facts are biased toward sentences containing commas, colons or parentheses. Fix: replace that check with a minimum word count, regenerate the kit (`python -m eval.build_question_kit`), re-read section B, rerun the tests (one test compares the committed kit file with the generator output), then commit the three files.
- Handing the kit to Gemini is the owner's action; nothing here sends anything anywhere.

## Open decisions (owner)
1. Confirm the 8 / 10 / 8 / 4 mapping (and so the total of 30 vs the earlier 50); then I update `golden_check` targets and the README.
2. Do the 38 model drafts still get reviewed (keep / cut / choose `expected_doc_ids`), or does the Gemini route replace them?
3. Write the `exact_term` and `unanswerable` questions into `eval/golden_owner.jsonl` (check with `python -m eval.golden_check`; overlap with `python -m eval.overlap_check`).
4. Checkpoint 3: start the native-RRF trial licence yourself (`POST _license/start_trial?acknowledge=true`); the cluster is on the basic licence. Needed only for the native vs Python cross-check.
5. Checkpoint 4 (later): hand-label 25 verifier judgements; checkpoint 5: README results and CV bullet only after you have seen the saved eval outputs.

## Next steps
1. Me: fix `extract_fact`, regenerate and re-read the kit, run the full suite, commit the kit.
2. You: answer the decisions above; produce the final `eval/golden.jsonl` (I renumber ids to `q001`...).
3. Then Phase 7: `eval/retrieval_eval.py` (exhausted-list rule from `eval/metrics.py`, pool sweep 50/100/200, six chunker x mode rows split by question type), `eval/answer_eval.py`, the checkpoint-4 sampler, then Phase 8 (API, Docker, separate small query-embedding cache because a cache miss streams the 273 MB file).

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
- Run `pytest -q` first: expect 1 failure until `extract_fact` is fixed (see above).
