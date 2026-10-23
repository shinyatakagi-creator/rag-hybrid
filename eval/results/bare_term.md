# Bare-term diagnostic (sensitivity analysis, not part of the golden-set baseline)

Git `a1dec2e` | 2026-10-23T05:03:49+00:00 | golden `eval/golden.jsonl` (sha256 `898d37e180c2`) | 16 questions scored (exact_term 8, mixed 8); 14 unanswerable excluded.

Query = the exact term alone, for the 16 exact_term and mixed questions; same 6 rows, same metrics, same expected docs. It shows how much of the baseline score on these questions comes from the surrounding words.

Doc-level metrics after dedupe. Recall@k = share of expected docs in the top k distinct docs; MRR = mean 1/rank of the first expected doc. Exhausted lists stay in the denominator as misses. n is small, so read differences with the intervals.

## Overall (n = 16 questions per row)

| row | n | Recall@5 | Recall@10 | Recall@10 95% CI | MRR | MRR 95% CI | exhausted | exhausted & missed | <10 docs |
|---|---|---|---|---|---|---|---|---|---|
| fixed/bm25 | 16 | 0.875 | 0.938 | 0.812-1.000 | 0.651 | 0.474-0.823 | 9 | 0 | 8 |
| fixed/dense | 16 | 0.469 | 0.656 | 0.438-0.875 | 0.331 | 0.172-0.511 | 0 | 0 | 0 |
| fixed/hybrid | 16 | 0.875 | 0.938 | 0.812-1.000 | 0.487 | 0.340-0.651 | 0 | 0 | 0 |
| heading/bm25 | 16 | 0.875 | 1.000 | 1.000-1.000 | 0.619 | 0.451-0.792 | 9 | 0 | 8 |
| heading/dense | 16 | 0.500 | 0.719 | 0.500-0.906 | 0.344 | 0.187-0.525 | 0 | 0 | 0 |
| heading/hybrid | 16 | 0.938 | 1.000 | 1.000-1.000 | 0.610 | 0.440-0.786 | 0 | 0 | 0 |

Bootstrap: percentile, 10,000 resamples of the questions, seed 0. A hybrid row is never exhausted by construction (its dense list always fills the window); its exhausted count is 0 and says nothing about the BM25 half.

## By question type

### exact_term (n = 8)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/bm25 | 8 | 0.875 | 0.875 | 0.552 | 5 | 0 |
| fixed/dense | 8 | 0.438 | 0.562 | 0.192 | 0 | 0 |
| fixed/hybrid | 8 | 0.875 | 1.000 | 0.397 | 0 | 0 |
| heading/bm25 | 8 | 0.750 | 1.000 | 0.540 | 5 | 0 |
| heading/dense | 8 | 0.500 | 0.812 | 0.226 | 0 | 0 |
| heading/hybrid | 8 | 0.875 | 1.000 | 0.591 | 0 | 0 |

### mixed (n = 8)

| row | n | Recall@5 | Recall@10 | MRR | exhausted | exhausted & missed |
|---|---|---|---|---|---|---|
| fixed/bm25 | 8 | 0.875 | 1.000 | 0.750 | 4 | 0 |
| fixed/dense | 8 | 0.500 | 0.750 | 0.470 | 0 | 0 |
| fixed/hybrid | 8 | 0.875 | 0.875 | 0.577 | 0 | 0 |
| heading/bm25 | 8 | 1.000 | 1.000 | 0.698 | 4 | 0 |
| heading/dense | 8 | 0.500 | 0.625 | 0.461 | 0 | 0 |
| heading/hybrid | 8 | 1.000 | 1.000 | 0.629 | 0 | 0 |

## Tiny-chunk diagnostic (top 5 chunks per question, tiny = under 100 tokens)

| row | top-5 chunks | tiny | tiny share | tiny from an expected doc | share of tiny | questions with one |
|---|---|---|---|---|---|---|
| fixed/bm25 | 72 | 0 | 0.0% | 0 | 0.0% | 0 of 16 |
| fixed/dense | 80 | 10 | 12.5% | 0 | 0.0% | 0 of 16 |
| fixed/hybrid | 80 | 3 | 3.8% | 0 | 0.0% | 0 of 16 |
| heading/bm25 | 71 | 2 | 2.8% | 1 | 50.0% | 1 of 16 |
| heading/dense | 80 | 9 | 11.2% | 0 | 0.0% | 0 of 16 |
| heading/hybrid | 80 | 7 | 8.8% | 2 | 28.6% | 2 of 16 |

## Per-question rank of the first expected doc (distinct docs; `-` = not returned)

| id | type | fixed/bm25 | fixed/dense | fixed/hybrid | heading/bm25 | heading/dense | heading/hybrid |
|---|---|---|---|---|---|---|---|
| e001 | exact_term | 1 | 40 | 5 | 1 | 7 | 1 |
| e002 | exact_term | 4 | 4 | 4 | 5 | 6 | 7 |
| e003 | exact_term | 12 | 27 | 7 | 7 | 4 | 4 |
| e004 | exact_term | 3 | 15 | 2 | 3 | 25 | 2 |
| e005 | exact_term | 4 | 3 | 3 | 7 | 3 | 3 |
| e006 | exact_term | 1 | 8 | 4 | 1 | 4 | 1 |
| e007 | exact_term | 2 | 5 | 1 | 2 | 8 | 2 |
| e008 | exact_term | 1 | 2 | 2 | 1 | 2 | 1 |
| m001 | mixed | 1 | 7 | 2 | 2 | 9 | 3 |
| m002 | mixed | 1 | 1 | 1 | 1 | 1 | 1 |
| m003 | mixed | 2 | 10 | 3 | 4 | 18 | 4 |
| m004 | mixed | 1 | 1 | 1 | 1 | 1 | 1 |
| m005 | mixed | 1 | 1 | 1 | 1 | 1 | 1 |
| m006 | mixed | 1 | 2 | 2 | 1 | 2 | 1 |
| m007 | mixed | 6 | 65 | 12 | 2 | 42 | 5 |
| m008 | mixed | 3 | - | 5 | 3 | - | 4 |

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
 "query_embeddings_api_calls_this_run": 1,
 "query_embeddings_est_spend_usd": 1.62e-06,
 "query": "the question's exact_term field alone, e.g. '--root-ca-file'",
 "queries": {
  "e001": "--remove-extra-subjects",
  "e002": "--service-account-max-token-expiration",
  "e003": "--bind-address",
  "e004": "acquireTime",
  "e005": "preBind",
  "e006": "compositePodGroupTemplates",
  "e007": "node.cloudprovider.kubernetes.io/uninitialized",
  "e008": "authentication.kubernetes.io/mutatingwebhookconfiguration-uid",
  "m001": "--root-ca-file",
  "m002": "--enable-priority-and-fairness",
  "m003": "--certificate-identity",
  "m004": "schedulingGates",
  "m005": "topologySpreadConstraints",
  "m006": "bindMountOptions",
  "m007": "kubernetes.io/bootstrapping",
  "m008": "OOMKilled"
 }
}
```
