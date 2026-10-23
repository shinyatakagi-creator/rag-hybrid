# Retrieval baseline

Git `535f3d9` | 2026-10-23T04:50:55+00:00 | golden `eval/golden.jsonl` (sha256 `898d37e180c2`) | 26 answerable questions (exact_term 8, mixed 8, conceptual 10); 4 unanswerable excluded.

Doc-level metrics after dedupe. Recall@k = share of expected docs in the top k distinct docs; MRR = mean 1/rank of the first expected doc. Exhausted lists stay in the denominator as misses. Baseline only: no tuning. n is small, so read differences with the intervals.

## Overall (n = 26 questions per row)

| row | n | Recall@5 | Recall@10 | Recall@10 95% CI | MRR | MRR 95% CI | exhausted | exhausted & missed | <10 docs |
|---|---|---|---|---|---|---|---|---|---|
| fixed/bm25 | 26 | 0.577 | 0.615 | 0.423-0.808 | 0.554 | 0.372-0.735 | 0 | 0 | 0 |
| fixed/dense | 26 | 0.821 | 0.865 | 0.731-0.981 | 0.654 | 0.499-0.804 | 0 | 0 | 0 |
| fixed/hybrid | 26 | 0.731 | 0.788 | 0.635-0.923 | 0.601 | 0.441-0.764 | 0 | 0 | 0 |
| heading/bm25 | 26 | 0.635 | 0.673 | 0.500-0.846 | 0.524 | 0.358-0.693 | 0 | 0 | 0 |
| heading/dense | 26 | 0.769 | 0.878 | 0.750-0.981 | 0.630 | 0.489-0.772 | 0 | 0 | 0 |
| heading/hybrid | 26 | 0.788 | 0.827 | 0.692-0.962 | 0.640 | 0.488-0.795 | 0 | 0 | 0 |

Bootstrap: percentile, 10,000 resamples of the questions, seed 0. Hybrid is never exhausted by construction (its dense list always fills the window); its exhausted count is 0 and says nothing about the BM25 half.

## By question type

### exact_term (n = 8)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/bm25 | 8 | 1.000 | 1.000 | 0.875 | 0 | 0 |
| fixed/dense | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| fixed/hybrid | 8 | 1.000 | 1.000 | 0.938 | 0 | 0 |
| heading/bm25 | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| heading/dense | 8 | 0.938 | 1.000 | 0.729 | 0 | 0 |
| heading/hybrid | 8 | 1.000 | 1.000 | 0.875 | 0 | 0 |

### mixed (n = 8)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/bm25 | 8 | 0.875 | 1.000 | 0.889 | 0 | 0 |
| fixed/dense | 8 | 1.000 | 1.000 | 0.838 | 0 | 0 |
| fixed/hybrid | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| heading/bm25 | 8 | 0.875 | 0.875 | 0.760 | 0 | 0 |
| heading/dense | 8 | 0.875 | 1.000 | 0.826 | 0 | 0 |
| heading/hybrid | 8 | 1.000 | 1.000 | 0.906 | 0 | 0 |

### conceptual (n = 10)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/bm25 | 10 | 0.000 | 0.000 | 0.028 | 0 | 0 |
| fixed/dense | 10 | 0.533 | 0.650 | 0.347 | 0 | 0 |
| fixed/hybrid | 10 | 0.300 | 0.450 | 0.129 | 0 | 0 |
| heading/bm25 | 10 | 0.150 | 0.250 | 0.072 | 0 | 0 |
| heading/dense | 10 | 0.550 | 0.683 | 0.393 | 0 | 0 |
| heading/hybrid | 10 | 0.450 | 0.550 | 0.240 | 0 | 0 |

## Paired comparison: rank of the first expected doc, hybrid vs a single mode

win = hybrid ranks the first expected doc better, loss = worse, tie = same rank (including both missing).

| comparison | scope | n | wins | ties | losses |
|---|---|---|---|---|---|
| fixed: hybrid vs bm25 | overall | 26 | 11 | 13 | 2 |
| fixed: hybrid vs bm25 | exact_term | 8 | 1 | 7 | 0 |
| fixed: hybrid vs bm25 | mixed | 8 | 1 | 6 | 1 |
| fixed: hybrid vs bm25 | conceptual | 10 | 9 | 0 | 1 |
| fixed: hybrid vs dense | overall | 26 | 4 | 15 | 7 |
| fixed: hybrid vs dense | exact_term | 8 | 1 | 7 | 0 |
| fixed: hybrid vs dense | mixed | 8 | 1 | 7 | 0 |
| fixed: hybrid vs dense | conceptual | 10 | 2 | 1 | 7 |
| heading: hybrid vs bm25 | overall | 26 | 13 | 12 | 1 |
| heading: hybrid vs bm25 | exact_term | 8 | 1 | 7 | 0 |
| heading: hybrid vs bm25 | mixed | 8 | 3 | 5 | 0 |
| heading: hybrid vs bm25 | conceptual | 10 | 9 | 0 | 1 |
| heading: hybrid vs dense | overall | 26 | 7 | 12 | 7 |
| heading: hybrid vs dense | exact_term | 8 | 3 | 5 | 0 |
| heading: hybrid vs dense | mixed | 8 | 2 | 6 | 0 |
| heading: hybrid vs dense | conceptual | 10 | 2 | 1 | 7 |

## Tiny-chunk diagnostic (top 5 chunks per question, tiny = under 100 tokens)

| row | top-5 chunks | tiny | tiny share | tiny from an expected doc | share of tiny | questions with one |
|---|---|---|---|---|---|---|
| fixed/bm25 | 130 | 0 | 0.0% | 0 | 0.0% | 0 of 26 |
| fixed/dense | 130 | 5 | 3.8% | 0 | 0.0% | 0 of 26 |
| fixed/hybrid | 130 | 1 | 0.8% | 0 | 0.0% | 0 of 26 |
| heading/bm25 | 130 | 7 | 5.4% | 2 | 28.6% | 2 of 26 |
| heading/dense | 130 | 8 | 6.2% | 3 | 37.5% | 3 of 26 |
| heading/hybrid | 130 | 12 | 9.2% | 4 | 33.3% | 3 of 26 |

## Per-question rank of the first expected doc (distinct docs; `-` = not returned)

| id | type | fixed/bm25 | fixed/dense | fixed/hybrid | heading/bm25 | heading/dense | heading/hybrid |
|---|---|---|---|---|---|---|---|
| e001 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 |
| e002 | exact_term | 2 | 1 | 1 | 3 | 3 | 2 |
| e003 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 |
| e004 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 |
| e005 | exact_term | 1 | 1 | 1 | 1 | 2 | 1 |
| e006 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 |
| e007 | exact_term | 2 | 2 | 2 | 2 | 2 | 2 |
| e008 | exact_term | 1 | 3 | 1 | 1 | 2 | 1 |
| m001 | mixed | 1 | 1 | 1 | 1 | 1 | 1 |
| m002 | mixed | 1 | 1 | 1 | 1 | 1 | 1 |
| m003 | mixed | 1 | 1 | 1 | 1 | 1 | 1 |
| m004 | mixed | 1 | 1 | 1 | 2 | 1 | 1 |
| m005 | mixed | 1 | 1 | 1 | 2 | 1 | 1 |
| m006 | mixed | 1 | 2 | 2 | 1 | 2 | 1 |
| m007 | mixed | 1 | 1 | 1 | 1 | 1 | 1 |
| m008 | mixed | 9 | 5 | 3 | 13 | 9 | 4 |
| c001 | conceptual | 67 | 1 | 5 | 95 | 2 | 12 |
| c002 | conceptual | - | 8 | 19 | - | 4 | 11 |
| c003 | conceptual | 16 | 4 | 4 | 20 | 6 | 4 |
| c004 | conceptual | 26 | 33 | 22 | 9 | 2 | 5 |
| c005 | conceptual | 35 | 1 | 9 | 5 | 1 | 3 |
| c006 | conceptual | 70 | 3 | 6 | 54 | 3 | 5 |
| c007 | conceptual | 37 | 2 | 3 | 27 | 1 | 1 |
| c008 | conceptual | 18 | 5 | 11 | 21 | 8 | 11 |
| c009 | conceptual | - | 29 | 50 | - | 28 | 43 |
| c010 | conceptual | 23 | - | 55 | 4 | 59 | 8 |

## Settings

```json
{
 "index": "rag-docs",
 "es_version": "9.5.5",
 "docs_per_chunker": {
  "fixed": 4072,
  "heading": 4527
 },
 "embed_model": "text-embedding-3-small",
 "pool": 200,
 "knn": {
  "k": 200,
  "num_candidates": 800
 },
 "rrf_k": 60,
 "hybrid_fused_list": 400,
 "bm25_fields": [
  "title^2",
  "heading_path^1.5",
  "content"
 ],
 "bm25_window": 200,
 "ks": [
  5,
  10
 ],
 "tiny_chunk_tokens": 100,
 "bootstrap": {
  "n": 10000,
  "seed": 0,
  "method": "percentile, resampling questions"
 },
 "index_options": "as built (effective bbq_hnsw, rescore oversample 3.0; eval/results/mapping.json)",
 "fusion": "python",
 "query_embeddings_api_calls_this_run": 1,
 "query_embeddings_est_spend_usd": 1.382e-05
}
```
