# index_options sensitivity: bbq_hnsw (as built) vs explicit hnsw

Git `a1dec2e` | 2026-10-23T05:00:52+00:00 | golden `eval/golden.jsonl` (sha256 `898d37e180c2`) | 26 questions scored (exact_term 8, mixed 8, conceptual 10); 4 unanswerable excluded.

Same chunks and vectors (from the embedding cache, 0 embedding calls), same queries and settings; only the dense_vector index_options differ. BM25 does not depend on it, so only dense and hybrid rows are compared.

Doc-level metrics after dedupe. Recall@k = share of expected docs in the top k distinct docs; MRR = mean 1/rank of the first expected doc. Exhausted lists stay in the denominator as misses. n is small, so read differences with the intervals.

## Overall (n = 26 questions per row)

| row | n | Recall@5 | Recall@10 | Recall@10 95% CI | MRR | MRR 95% CI | exhausted | exhausted & missed | <10 docs |
|---|---|---|---|---|---|---|---|---|---|
| fixed/dense [bbq_hnsw] | 26 | 0.821 | 0.865 | 0.731-0.981 | 0.654 | 0.499-0.804 | 0 | 0 | 0 |
| fixed/hybrid [bbq_hnsw] | 26 | 0.731 | 0.788 | 0.635-0.923 | 0.601 | 0.441-0.764 | 0 | 0 | 0 |
| heading/dense [bbq_hnsw] | 26 | 0.769 | 0.878 | 0.750-0.981 | 0.630 | 0.489-0.772 | 0 | 0 | 0 |
| heading/hybrid [bbq_hnsw] | 26 | 0.788 | 0.827 | 0.692-0.962 | 0.640 | 0.488-0.795 | 0 | 0 | 0 |
| fixed/dense [hnsw] | 26 | 0.821 | 0.865 | 0.731-0.981 | 0.654 | 0.499-0.804 | 0 | 0 | 0 |
| fixed/hybrid [hnsw] | 26 | 0.731 | 0.788 | 0.635-0.923 | 0.601 | 0.442-0.765 | 0 | 0 | 0 |
| heading/dense [hnsw] | 26 | 0.769 | 0.878 | 0.750-0.981 | 0.630 | 0.489-0.772 | 0 | 0 | 0 |
| heading/hybrid [hnsw] | 26 | 0.788 | 0.827 | 0.692-0.962 | 0.640 | 0.488-0.795 | 0 | 0 | 0 |

Bootstrap: percentile, 10,000 resamples of the questions, seed 0. A hybrid row is never exhausted by construction (its dense list always fills the window); its exhausted count is 0 and says nothing about the BM25 half.

## By question type

### exact_term (n = 8)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/dense [bbq_hnsw] | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| fixed/hybrid [bbq_hnsw] | 8 | 1.000 | 1.000 | 0.938 | 0 | 0 |
| heading/dense [bbq_hnsw] | 8 | 0.938 | 1.000 | 0.729 | 0 | 0 |
| heading/hybrid [bbq_hnsw] | 8 | 1.000 | 1.000 | 0.875 | 0 | 0 |
| fixed/dense [hnsw] | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| fixed/hybrid [hnsw] | 8 | 1.000 | 1.000 | 0.938 | 0 | 0 |
| heading/dense [hnsw] | 8 | 0.938 | 1.000 | 0.729 | 0 | 0 |
| heading/hybrid [hnsw] | 8 | 1.000 | 1.000 | 0.875 | 0 | 0 |

### mixed (n = 8)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/dense [bbq_hnsw] | 8 | 1.000 | 1.000 | 0.838 | 0 | 0 |
| fixed/hybrid [bbq_hnsw] | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| heading/dense [bbq_hnsw] | 8 | 0.875 | 1.000 | 0.826 | 0 | 0 |
| heading/hybrid [bbq_hnsw] | 8 | 1.000 | 1.000 | 0.906 | 0 | 0 |
| fixed/dense [hnsw] | 8 | 1.000 | 1.000 | 0.838 | 0 | 0 |
| fixed/hybrid [hnsw] | 8 | 1.000 | 1.000 | 0.854 | 0 | 0 |
| heading/dense [hnsw] | 8 | 0.875 | 1.000 | 0.826 | 0 | 0 |
| heading/hybrid [hnsw] | 8 | 1.000 | 1.000 | 0.906 | 0 | 0 |

### conceptual (n = 10)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/dense [bbq_hnsw] | 10 | 0.533 | 0.650 | 0.347 | 0 | 0 |
| fixed/hybrid [bbq_hnsw] | 10 | 0.300 | 0.450 | 0.129 | 0 | 0 |
| heading/dense [bbq_hnsw] | 10 | 0.550 | 0.683 | 0.393 | 0 | 0 |
| heading/hybrid [bbq_hnsw] | 10 | 0.450 | 0.550 | 0.240 | 0 | 0 |
| fixed/dense [hnsw] | 10 | 0.533 | 0.650 | 0.347 | 0 | 0 |
| fixed/hybrid [hnsw] | 10 | 0.300 | 0.450 | 0.130 | 0 | 0 |
| heading/dense [hnsw] | 10 | 0.550 | 0.683 | 0.393 | 0 | 0 |
| heading/hybrid [hnsw] | 10 | 0.450 | 0.550 | 0.240 | 0 | 0 |

## Tiny-chunk diagnostic (top 5 chunks per question, tiny = under 100 tokens)

| row | top-5 chunks | tiny | tiny share | tiny from an expected doc | share of tiny | questions with one |
|---|---|---|---|---|---|---|
| fixed/dense [bbq_hnsw] | 130 | 5 | 3.8% | 0 | 0.0% | 0 of 26 |
| fixed/hybrid [bbq_hnsw] | 130 | 1 | 0.8% | 0 | 0.0% | 0 of 26 |
| heading/dense [bbq_hnsw] | 130 | 8 | 6.2% | 3 | 37.5% | 3 of 26 |
| heading/hybrid [bbq_hnsw] | 130 | 12 | 9.2% | 4 | 33.3% | 3 of 26 |
| fixed/dense [hnsw] | 130 | 5 | 3.8% | 0 | 0.0% | 0 of 26 |
| fixed/hybrid [hnsw] | 130 | 1 | 0.8% | 0 | 0.0% | 0 of 26 |
| heading/dense [hnsw] | 130 | 8 | 6.2% | 3 | 37.5% | 3 of 26 |
| heading/hybrid [hnsw] | 130 | 12 | 9.2% | 4 | 33.3% | 3 of 26 |

## Per-question rank of the first expected doc (distinct docs; `-` = not returned)

| id | type | fixed/dense [bbq_hnsw] | fixed/hybrid [bbq_hnsw] | heading/dense [bbq_hnsw] | heading/hybrid [bbq_hnsw] | fixed/dense [hnsw] | fixed/hybrid [hnsw] | heading/dense [hnsw] | heading/hybrid [hnsw] |
|---|---|---|---|---|---|---|---|---|---|
| e001 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| e002 | exact_term | 1 | 1 | 3 | 2 | 1 | 1 | 3 | 2 |
| e003 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| e004 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| e005 | exact_term | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 |
| e006 | exact_term | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| e007 | exact_term | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| e008 | exact_term | 3 | 1 | 2 | 1 | 3 | 1 | 2 | 1 |
| m001 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m002 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m003 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m004 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m005 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m006 | mixed | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 1 |
| m007 | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| m008 | mixed | 5 | 3 | 9 | 4 | 5 | 3 | 9 | 4 |
| c001 | conceptual | 1 | 5 | 2 | 12 | 1 | 5 | 2 | 12 |
| c002 | conceptual | 8 | 19 | 4 | 11 | 8 | 19 | 4 | 11 |
| c003 | conceptual | 4 | 4 | 6 | 4 | 4 | 4 | 6 | 4 |
| c004 | conceptual | 33 | 22 | 2 | 5 | 33 | 22 | 2 | 5 |
| c005 | conceptual | 1 | 9 | 1 | 3 | 1 | 8 | 1 | 3 |
| c006 | conceptual | 3 | 6 | 3 | 5 | 3 | 6 | 3 | 5 |
| c007 | conceptual | 2 | 3 | 1 | 1 | 2 | 3 | 1 | 1 |
| c008 | conceptual | 5 | 11 | 8 | 11 | 5 | 11 | 8 | 11 |
| c009 | conceptual | 29 | 50 | 28 | 43 | 29 | 50 | 28 | 43 |
| c010 | conceptual | - | 55 | 59 | 8 | - | 55 | 59 | 8 |

## Agreement between the two indexes

Mean share of the top-10 chunk ids two indexes return for the same query (dense list and fused hybrid list).

| chunker | mode | top-10 chunk overlap | questions with a different first expected-doc rank |
|---|---|---|---|
| fixed | dense | 1.000 | 0 of 26 |
| fixed | hybrid | 0.992 | 1 of 26 |
| heading | dense | 1.000 | 0 of 26 |
| heading | hybrid | 1.000 | 0 of 26 |

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
 "index_options": "compared: rag-docs = default (effective bbq_hnsw, m16, ef100, rescore oversample 3.0) vs rag-docs-hnsw = explicit hnsw (m16, ef_construction 100, no quantisation)",
 "fusion": "python",
 "query_embeddings_api_calls_this_run": 0,
 "query_embeddings_est_spend_usd": 0.0,
 "hnsw_index": "rag-docs-hnsw",
 "hnsw_options": {
  "type": "hnsw",
  "m": 16,
  "ef_construction": 100
 },
 "store_bytes": {
  "rag-docs": 64051101,
  "rag-docs-hnsw": 62491153
 },
 "mapping_hnsw": "eval/results/mapping_hnsw.json",
 "query_time": "kNN k=200, num_candidates=800 on both indexes"
}
```
