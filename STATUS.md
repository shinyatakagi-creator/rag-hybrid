# Status (end of day 2)

Phases 0-6 are built; Phase 7 (eval) has not been started. Run `git log --oneline` for the exact head; see `NOTES.md` for every deviation from the guide.

## Phases done

| Phase | Commit(s) | Notes |
|---|---|---|
| 0 Setup | `b9d3d05` | ES 9.5.5, 1 GB heap, Kibana under `--profile debug`, pinned deps |
| 1 Chunking | `809c63d`, `14655bf`, `3959f71`, `5eb9cf4`, `3ca1f19` | Final rules: "What's next" sections stripped in the loader, headless include partials excluded, front-matter-at-EOF bug fixed. **502 pages, 477 with chunks; 4,087 fixed / 4,528 heading chunks** (`docs/CORPUS.md`, `eval/results/phase1_stats.txt`) |
| 2 Index | `a23ab0b`, `053ea2d`, `2b21f82`, `3ca1f19` | `rag-docs` = 8,615 docs, counts match the chunk files; `eval/results/mapping.json` (`bbq_hnsw`); a rerun makes 0 embedding calls |
| 3+4 Retrieval + Python RRF | `519a55a` | bm25 / dense / hybrid, chunker-filtered; own RRF (k=60); window raised to 200 in `cf704d8` |
| 5 Generation | `cf704d8` | Cited, validated structured answers (`claude-sonnet-5-5`) |
| 6 Verification | `bc853f1`, then the latest commit | `claude-haiku-5-5`, one batched call per answer, validated; mutation test + controls. Results in `NOTES.md` (Phase 6) |

## Where Phase 6 landed
- Mutation test: 10 wrong pairs -> 7 `no`, 3 `partial`, 0 missed; 5 controls -> 5 `yes`, 0 false alarms.
- Saved answers: citation precision 0.57 and 0.60, but at least 3 of the 5 `partial`s look like false alarms to me, so the verifier is noisy on paraphrased sentences. The pid-limiting sentence citing [4] is `yes` (correct); the verifier cannot see that it is only loosely relevant.
- Hard-refusal question (answer only in an excluded page): the model refused.

## Open items
1. **Checkpoint 4 (yours): hand-label 25 verifier judgements** before any verifier number is quoted. Not built yet: a sampler that prints 25 (sentence, chunk, verdict) triples and computes agreement from your labels. With only 12 real pairs in the saved answers, I would generate more answers first (a paid step, to be estimated and confirmed).
2. **`partial` is a loose bucket** (it labels some faithful paraphrases and some contradicted sentences). Decide whether to tighten the verifier prompt (and re-run the mutation test) or report only `yes` vs not-`yes`.
3. **BM25 exhausted-list rule**: implemented in `eval/metrics.py`; to be wired into `eval/retrieval_eval.py` in Phase 7.
4. **Pool sweep** (50/100/200) on the golden set before stating any hybrid result (window changes dense accuracy and RRF order, see `NOTES.md` Phase 4b).
5. **Phase 8 query-cache note**: plan written, no code.

## Decisions / work pending from you
- **Golden set (checkpoint 2):** you write the `exact_term` and `unanswerable` questions; I draft only `conceptual` and `mixed` (with the `eval/overlap.py` check) and stop for you to choose the `expected_doc_ids`. The corpus is now fixed at the 502 pages above, so the set can be written against it.
- **Native RRF (checkpoint 3):** you start the trial licence (`POST _license/start_trial?acknowledge=true`); the cluster is on the basic licence.

## Next step
Phase 7 (eval), but its inputs are not ready: it needs the golden set (yours to write/choose) and, for the answer-eval half, the checkpoint-4 hand labels. I can build `eval/retrieval_eval.py` (no paid calls except query embeddings) in the meantime.

## Spend so far (about $0.106 of the $5 limit)
| Item | Cost | Source |
|---|---|---|
| Corpus embeddings, first run (2,750,672 tokens) | $0.0550 | API-reported |
| Re-embed after the What's-next rule (66,058 tokens) | $0.0013 | API-reported |
| Query embeddings (~652 tokens) | $0.000013 | token-count estimate |
| Answer generation, 4 questions | $0.0477 | usage fields |
| Verification of saved answers, 2 calls | $0.0009 | usage fields |
| Mutation test + controls, 2 calls | $0.0012 | usage fields |
| **Total** | **about $0.1061** | |

`MAX_SPEND_USD` is enforced per run, not cumulatively.

## Resuming
- ES container `rag-hybrid-es-1`; `rag-docs` lives in a Docker volume (`docker compose up -d` if Docker was restarted).
- Local only, not in git: `.env` (both keys), `data/` (corpus checkout, chunks, the embedding cache). Activate with `source .venv/bin/activate`.
