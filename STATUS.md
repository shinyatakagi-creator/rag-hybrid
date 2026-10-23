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
- **Verifier rubric v2 (`claims-v2`)**: the model lists each sentence's claims and marks them supported / unsupported / contradicted; the verdict (yes / partial / no) is derived in code. v1's loose `partial` is gone (v1 results kept in `eval/results/verify_mutation_v1.json`).
- **Dev set (25 pairs; not an accuracy figure, v2 was written after seeing v1's failures on it)**: Haiku 10/10 wrong pairs `no`, 5/5 verbatim controls `yes`, 10/10 paraphrased controls `yes`. Sonnet 5.5 as verifier agrees on 25/25 pairs (claim lists identical on 16/25). Haiku stays the verifier (Sonnet cost 17x more).
- **Saved answers under v2**: citation precision 6/7 = 0.86 and 5/5 = 1.00 (v1: 0.57, 0.60). The pid-limiting sentence citing [4] is `yes`. One `partial` remains (row 0, the "reserve PIDs ... so that the kubelet is protected" sentence), a good case for your hand labels. Not a faithfulness number: 12 pairs.
- Hard-refusal question (answer only in an excluded page): the model refused.

## Open items
1. **Checkpoint 4 (yours): hand-label 25 verifier judgements** before any verifier number is quoted. Not built yet: a sampler that prints 25 (sentence, chunk, verdict) triples and computes agreement from your labels. With only 12 real pairs in the saved answers, I would generate more answers first (a paid step, to be estimated and confirmed).
2. ~~`partial` is a loose bucket~~ Addressed by rubric v2 (claims + derived verdict). The real test is your hand labels: v2 has only been checked on my hand-built dev set and 12 real pairs.
3. **BM25 exhausted-list rule**: implemented in `eval/metrics.py`; to be wired into `eval/retrieval_eval.py` in Phase 7.
4. **Pool sweep** (50/100/200) on the golden set before stating any hybrid result (window changes dense accuracy and RRF order, see `NOTES.md` Phase 4b).
5. **Phase 8 query-cache note**: plan written, no code.

## Decisions / work pending from you
- **Golden set (checkpoint 2):** you write the `exact_term` and `unanswerable` questions; I draft only `conceptual` and `mixed` (with the `eval/overlap.py` check) and stop for you to choose the `expected_doc_ids`. The corpus is now fixed at the 502 pages above, so the set can be written against it.
- **Native RRF (checkpoint 3):** you start the trial licence (`POST _license/start_trial?acknowledge=true`); the cluster is on the basic licence.

## Next step
Phase 7 (eval), but its inputs are not ready: it needs the golden set (yours to write/choose) and, for the answer-eval half, the checkpoint-4 hand labels. I can build `eval/retrieval_eval.py` (no paid calls except query embeddings) in the meantime.

## Spend so far (about $0.150 of the $5 limit)
| Item | Cost | Source |
|---|---|---|
| Embeddings: corpus (2,750,672 tokens) + re-embed (66,058) + queries (~652, estimated) | $0.0563 | API-reported / estimate |
| Answer generation, 4 questions | $0.0477 | usage fields |
| Verification rows 0,1 (v1) | $0.0009 | usage fields |
| Mutation test v1 (15 pairs, Haiku) | $0.0012 | usage fields |
| Verification rows 0,1 (v2, Haiku) | $0.0014 | usage fields |
| Mutation set v2, 25 pairs, Haiku | $0.0023 | usage fields |
| Mutation set v2, 25 pairs, Sonnet 5.5 cross-check | $0.0405 | usage fields |
| **Total** | **about $0.1503** | |

`MAX_SPEND_USD` is enforced per run, not cumulatively.

## Resuming
- ES container `rag-hybrid-es-1`; `rag-docs` lives in a Docker volume (`docker compose up -d` if Docker was restarted).
- Local only, not in git: `.env` (both keys), `data/` (corpus checkout, chunks, the embedding cache). Activate with `source .venv/bin/activate`.
