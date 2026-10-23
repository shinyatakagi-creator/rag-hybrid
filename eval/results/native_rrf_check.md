# Native rrf retriever vs Python RRF

Git `5ffd9d8` | ES 9.5.5 | license trial (expires 2026-11-22) | 26 answerable questions x 2 chunkers. rank_constant 60, rank_window_size 200, same filters and inner retrievers; query vectors from the cache (0 embedding calls).

| chunker | n | first expected-doc rank identical | top-10 docs identical order | top-10 chunks identical order | mean / min top-10 doc overlap |
|---|---|---|---|---|---|
| fixed | 26 | 26 of 26 | 25 of 26 | 24 of 26 | 10.00 / 10 of 10 |
| heading | 26 | 26 of 26 | 24 of 26 | 24 of 26 | 9.96 / 9 of 10 |

## Questions that differ in any way

| id | chunker | doc overlap | first rank py / native | first differing chunk position | adjacent score ties (py) |
|---|---|---|---|---|---|
| e005 | fixed | 10/10 | 1 / 1 | 2 | 1 |
| m004 | fixed | 10/10 | 1 / 1 | 10 | 1 |
| e005 | heading | 10/10 | 1 / 1 | 9 | 1 |
| m001 | heading | 10/10 | 1 / 1 | 4 | 1 |

## Why they differ

Every difference comes from an exact RRF score tie: two chunks whose rank pairs sum to the same value (for example BM25 rank 2 + dense rank 3 vs BM25 rank 3 + dense rank 2, or BM25 rank 2 + absent vs absent + dense rank 2). Python sums exact fractions, so these are true ties and it keeps the first-seen order (BM25 list order, then dense). The native retriever scores in float32 (scores agree to about 1e-9) and breaks ties its own way, and in these cases the order of the tied pair is swapped. In one case (m004, heading) the tied pair straddles position 10/11, so the 10th distinct doc differs (9 of 10 docs in common). In no case does a non-tied chunk move, the same chunks are in the fused window, and the first expected-doc rank is identical for all 52 question x chunker pairs, so the Recall and MRR figures would be the same under the native retriever.

## Settings

```json
{
 "rank_constant": 60,
 "rank_window_size": 200,
 "bm25_fields": [
  "title^2",
  "heading_path^1.5",
  "content"
 ],
 "knn": {
  "k": 200,
  "num_candidates": 800
 },
 "python_fused_list_chunks": 400,
 "native_size": 200,
 "index": "rag-docs",
 "n_questions": 26,
 "embedding_calls": 0
}
```
