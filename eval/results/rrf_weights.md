# Weighted RRF sensitivity (not tuning; no weight is chosen)

Git `a1dec2e` | 2026-10-23T05:00:44+00:00 | golden `eval/golden.jsonl` (sha256 `898d37e180c2`) | 26 questions scored (exact_term 8, mixed 8, conceptual 10); 4 unanswerable excluded.

Hybrid = Python RRF (k=60) with the dense list weighted 1, 1.5 or 2 and the BM25 list weighted 1. Weight 1 is the baseline fusion (reproduces the baseline hybrid rows exactly: True). bm25 and dense rows are repeated for reference.

Doc-level metrics after dedupe. Recall@k = share of expected docs in the top k distinct docs; MRR = mean 1/rank of the first expected doc. Exhausted lists stay in the denominator as misses. n is small, so read differences with the intervals.

## Overall (n = 26 questions per row)

| row | n | Recall@5 | Recall@10 | Recall@10 95% CI | MRR | MRR 95% CI | exhausted | exhausted & missed | <10 docs |
|---|---|---|---|---|---|---|---|---|---|
| fixed/bm25 | 26 | 0.577 | 0.615 | 0.423-0.808 | 0.554 | 0.372-0.735 | 0 | 0 | 0 |
| fixed/dense | 26 | 0.821 | 0.865 | 0.731-0.981 | 0.654 | 0.499-0.804 | 0 | 0 | 0 |
| heading/bm25 | 26 | 0.635 | 0.673 | 0.500-0.846 | 0.524 | 0.358-0.693 | 0 | 0 | 0 |
| heading/dense | 26 | 0.769 | 0.878 | 0.750-0.981 | 0.630 | 0.489-0.772 | 0 | 0 | 0 |
| fixed/hybrid w1 | 26 | 0.731 | 0.788 | 0.635-0.923 | 0.601 | 0.441-0.764 | 0 | 0 | 0 |
| heading/hybrid w1 | 26 | 0.788 | 0.827 | 0.692-0.962 | 0.640 | 0.488-0.795 | 0 | 0 | 0 |
| fixed/hybrid w1.5 | 26 | 0.788 | 0.821 | 0.667-0.962 | 0.627 | 0.474-0.781 | 0 | 0 | 0 |
| heading/hybrid w1.5 | 26 | 0.788 | 0.865 | 0.731-0.981 | 0.656 | 0.507-0.805 | 0 | 0 | 0 |
| fixed/hybrid w2 | 26 | 0.788 | 0.821 | 0.667-0.962 | 0.649 | 0.495-0.802 | 0 | 0 | 0 |
| heading/hybrid w2 | 26 | 0.788 | 0.865 | 0.731-0.981 | 0.650 | 0.501-0.801 | 0 | 0 | 0 |

Bootstrap: percentile, 10,000 resamples of the questions, seed 0. A hybrid row is never exhausted by construction (its dense list always fills the window); its exhausted count is 0 and says nothing about the BM25 half.

## By question type

### exact_term (n = 8)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/bm25 | 8 | 1.000 | 1.000 | 0.875 | 0 | 0 |
| fixed/dense | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| heading/bm25 | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| heading/dense | 8 | 0.938 | 1.000 | 0.729 | 0 | 0 |
| fixed/hybrid w1 | 8 | 1.000 | 1.000 | 0.938 | 0 | 0 |
| heading/hybrid w1 | 8 | 1.000 | 1.000 | 0.875 | 0 | 0 |
| fixed/hybrid w1.5 | 8 | 1.000 | 1.000 | 0.938 | 0 | 0 |
| heading/hybrid w1.5 | 8 | 1.000 | 1.000 | 0.875 | 0 | 0 |
| fixed/hybrid w2 | 8 | 1.000 | 1.000 | 0.938 | 0 | 0 |
| heading/hybrid w2 | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |

### mixed (n = 8)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/bm25 | 8 | 0.875 | 1.000 | 0.889 | 0 | 0 |
| fixed/dense | 8 | 1.000 | 1.000 | 0.838 | 0 | 0 |
| heading/bm25 | 8 | 0.875 | 0.875 | 0.760 | 0 | 0 |
| heading/dense | 8 | 0.875 | 1.000 | 0.826 | 0 | 0 |
| fixed/hybrid w1 | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| heading/hybrid w1 | 8 | 1.000 | 1.000 | 0.906 | 0 | 0 |
| fixed/hybrid w1.5 | 8 | 1.000 | 1.000 | 0.875 | 0 | 0 |
| heading/hybrid w1.5 | 8 | 1.000 | 1.000 | 0.900 | 0 | 0 |
| fixed/hybrid w2 | 8 | 1.000 | 1.000 | 0.875 | 0 | 0 |
| heading/hybrid w2 | 8 | 1.000 | 1.000 | 0.900 | 0 | 0 |

### conceptual (n = 10)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/bm25 | 10 | 0.000 | 0.000 | 0.028 | 0 | 0 |
| fixed/dense | 10 | 0.533 | 0.650 | 0.347 | 0 | 0 |
| heading/bm25 | 10 | 0.150 | 0.250 | 0.072 | 0 | 0 |
| heading/dense | 10 | 0.550 | 0.683 | 0.393 | 0 | 0 |
| fixed/hybrid w1 | 10 | 0.300 | 0.450 | 0.129 | 0 | 0 |
| heading/hybrid w1 | 10 | 0.450 | 0.550 | 0.240 | 0 | 0 |
| fixed/hybrid w1.5 | 10 | 0.450 | 0.533 | 0.180 | 0 | 0 |
| heading/hybrid w1.5 | 10 | 0.450 | 0.650 | 0.285 | 0 | 0 |
| fixed/hybrid w2 | 10 | 0.450 | 0.533 | 0.236 | 0 | 0 |
| heading/hybrid w2 | 10 | 0.450 | 0.650 | 0.288 | 0 | 0 |

## Tiny-chunk diagnostic (top 5 chunks per question, tiny = under 100 tokens)

| row | top-5 chunks | tiny | tiny share | tiny from an expected doc | share of tiny | questions with one |
|---|---|---|---|---|---|---|
| fixed/bm25 | 130 | 0 | 0.0% | 0 | 0.0% | 0 of 26 |
| fixed/dense | 130 | 5 | 3.8% | 0 | 0.0% | 0 of 26 |
| heading/bm25 | 130 | 7 | 5.4% | 2 | 28.6% | 2 of 26 |
| heading/dense | 130 | 8 | 6.2% | 3 | 37.5% | 3 of 26 |
| fixed/hybrid w1 | 130 | 1 | 0.8% | 0 | 0.0% | 0 of 26 |
| heading/hybrid w1 | 130 | 12 | 9.2% | 4 | 33.3% | 3 of 26 |
| fixed/hybrid w1.5 | 130 | 1 | 0.8% | 0 | 0.0% | 0 of 26 |
| heading/hybrid w1.5 | 130 | 13 | 10.0% | 4 | 30.8% | 3 of 26 |
| fixed/hybrid w2 | 130 | 2 | 1.5% | 0 | 0.0% | 0 of 26 |
| heading/hybrid w2 | 130 | 12 | 9.2% | 4 | 33.3% | 3 of 26 |

## Per-question rank of the first expected doc (distinct docs; `-` = not returned)

| id | type | fixed/bm25 | fixed/dense | heading/bm25 | heading/dense | fixed/hybrid w1 | heading/hybrid w1 | fixed/hybrid w1.5 | heading/hybrid w1.5 | fixed/hybrid w2 | heading/hybrid w2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| e001 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| e002 | exact_term | 2 | 1 | 3 | 3 | 1 | 2 | 1 | 2 | 1 | 3 |
| e003 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| e004 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| e005 | exact_term | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 |
| e006 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| e007 | exact_term | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| e008 | exact_term | 1 | 3 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 |
| m001 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m002 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m003 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m004 | mixed | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m005 | mixed | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m006 | mixed | 1 | 2 | 1 | 2 | 2 | 1 | 2 | 1 | 2 | 1 |
| m007 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m008 | mixed | 9 | 5 | 13 | 9 | 3 | 4 | 2 | 5 | 2 | 5 |
| c001 | conceptual | 67 | 1 | 95 | 2 | 5 | 12 | 5 | 9 | 5 | 7 |
| c002 | conceptual | - | 8 | - | 4 | 19 | 11 | 15 | 7 | 12 | 7 |
| c003 | conceptual | 16 | 4 | 20 | 6 | 4 | 4 | 3 | 3 | 4 | 3 |
| c004 | conceptual | 26 | 33 | 9 | 2 | 22 | 5 | 24 | 3 | 24 | 3 |
| c005 | conceptual | 35 | 1 | 5 | 1 | 9 | 3 | 4 | 2 | 3 | 2 |
| c006 | conceptual | 70 | 3 | 54 | 3 | 6 | 5 | 5 | 4 | 4 | 4 |
| c007 | conceptual | 37 | 2 | 27 | 1 | 3 | 1 | 2 | 1 | 1 | 1 |
| c008 | conceptual | 18 | 5 | 21 | 8 | 11 | 11 | 6 | 13 | 6 | 11 |
| c009 | conceptual | - | 29 | - | 28 | 50 | 43 | 38 | 37 | 35 | 32 |
| c010 | conceptual | 23 | - | 4 | 59 | 55 | 8 | 73 | 13 | 88 | 19 |

## Weighted RRF: change in the rank of the first expected doc relative to weight 1 (the baseline fusion)

Reported for every weight; no weight is picked. wins = the weighted fusion ranks the first expected doc better than weight 1.

| chunker | dense weight | wins | ties | losses |
|---|---|---|---|---|
| fixed | 1.5 | 8 | 16 | 2 |
| fixed | 2 | 7 | 17 | 2 |
| heading | 1.5 | 7 | 16 | 3 |
| heading | 2 | 7 | 16 | 3 |

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
 "index_options": "as built (effective bbq_hnsw)",
 "fusion": "python",
 "query_embeddings_api_calls_this_run": 0,
 "query_embeddings_est_spend_usd": 0.0,
 "dense_weights": [
  1,
  1.5,
  2
 ],
 "bm25_weight": 1,
 "weight_1_reproduces_baseline_hybrid": true
}
```
