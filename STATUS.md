# Status (end of day 1)

Last commit before this file: `cf704d8`. 92 tests passed at that commit. No Phase 6 work has been started.

## Phases done

| Phase | Commit(s) | Notes |
|---|---|---|
| 0 Setup | `b9d3d05` | ES 9.5.5, 1 GB heap, Kibana under `--profile debug`, pinned deps |
| 1 Chunking | `809c63d` (WIP), `14655bf` | Corpus scope B: 511 pages, 489 with chunks; 4,211 fixed / 4,824 heading chunks. Details in `NOTES.md`, `docs/CORPUS.md`, `eval/results/phase1_stats.txt` |
| 2 Index | `a23ab0b`, `053ea2d`, `2b21f82` | 9,035 docs in `rag-docs`, counts match chunk files; `eval/results/mapping.json` (effective `index_options` = `bbq_hnsw`); re-run makes 0 embedding calls |
| 3+4 Retrieval + Python RRF | `519a55a` | bm25 / dense / hybrid, chunker-filtered; own RRF (k=60) |
| 5 Generation | `cf704d8` | Cited, validated structured answers; also the 200-chunk retriever window (`eval/results/pool_check.txt`) and `eval/overlap.py` |

## Open items you raised, not done yet
1. **BM25 exhausted-list rule.** Remaining BM25 shortfalls (7 per chunker on the proxy queries) are rare identifiers that match only 1-14 chunks in the whole index. The rule for Phase 7 is written in `NOTES.md` ("report as list exhausted, not a window miss") but nothing in the eval code implements it yet.
2. **"Stop the Docker daemon" rank explanation.** Explained in `NOTES.md` (BM25 rank 2 on the word "Stop" + dense rank 9, so RRF puts a 37-token chunk first once kNN is near-exact), but you have not signed it off, and the 37-token chunk question ties into the tiny-chunk rule below.
3. **Hard refusal test.** The Terraform/AWS RDS refusal was an easy case (nothing related in the corpus). Still to do: a harder out-of-corpus question that sits next to the corpus (Kubernetes-adjacent, answer not in these docs) to see whether the model refuses or invents.
4. **Phase 8 query-cache note.** Plan is written in `NOTES.md` (a cache miss streams 273 MB, too slow for `/ask`: small separate query cache or a key-to-offset index). No code change yet.

## Decisions pending from you
- **Tiny-chunk rule, before the golden set.** Currently accepted as-is: 568 of 4,824 heading chunks (11.8%) are under 100 tokens, and fixed has 131 of 4,211 (3.1%). Phase 7 is to measure how often chunks under 100 tokens appear in the top 5 and whether any is a correct hit. You still need to confirm the final rule (keep, merge across H2 boundaries, or drop/skip "What's next" link lists) so the golden set is built against a fixed index.
- **Golden-set questions you are writing yourself:** the `exact_term` questions and the `unanswerable` ones. I draft only `conceptual` and `mixed`, with the `eval/overlap.py` check (checkpoint 2: you choose the final `expected_doc_ids`).

## Exact next step
Phase 6, citation verification, per the guide: one batched call per answer to the Haiku-class verifier (`VERIFIER_MODEL=claude-haiku-5-5`) asking yes / partial / no for each (sentence, cited chunk); report citation precision and the list of unsupported sentences; then print 25 sampled judgements (sentence, chunk, verdict) for you to hand-label (checkpoint 4) and compute agreement from your labels. Before any paid call: estimate, confirmation prompt, `MAX_SPEND_USD` guard. Your last message did not add Phase 6 instructions beyond the guide, so tell me if you want something different.

## Spend so far (about $0.095 of the $5 limit)
| Item | Cost | Source |
|---|---|---|
| Corpus embeddings (2,750,672 tokens, 91 calls) | $0.0550 | API-reported usage, `eval/results/embed_run.json` |
| Answer generation, 3 questions | $0.0402 | API-reported usage, `eval/results/generation_log.jsonl` |
| Query embeddings (about 632 tokens) | $0.0000126 | token-count estimate, not API-reported |
| **Total** | **about $0.0952** | |

`MAX_SPEND_USD` is enforced per run, not cumulatively.

## Resuming
- ES container `rag-hybrid-es-1` is still running with the `rag-docs` index in a Docker volume. If Docker was restarted: `docker compose up -d` (the index persists).
- Local only, not in git: `.env` (both API keys), `data/` (corpus checkout, chunks, the 273 MB embedding cache). Activate with `source .venv/bin/activate`.
