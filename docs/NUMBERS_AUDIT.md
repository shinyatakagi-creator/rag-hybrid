# Numbers audit

Generated from `docs/numbers_manifest.json` by `scripts/make_readme_tables.py`. Every digit in `README.md` lies inside one of the spans recorded in that manifest; `tests/test_readme_numbers.py` enforces it.

416 recorded spans in README.md: 358 from result files, 30 computed from them, 12 from prose docs, 16 typed constants.

## 1. From result files (and values computed from them)

| value | source file | key path | note | uses |
|---|---|---|---|---|
| 502 | `eval/results/chunk_stats.json` | `pages` |  | 2 |
| 477 | `eval/results/chunk_stats.json` | `fixed > docs` |  | 1 |
| 26 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > overall > n` |  | 7 |
| 9.5.5 | `eval/results/native_rrf_check.json` | `meta > es_version` |  | 1 |
| 4,072 | `eval/results/chunk_stats.json` | `fixed > chunks` |  | 1 |
| 4,527 | `eval/results/chunk_stats.json` | `heading > chunks` |  | 1 |
| 1536 | `eval/results/mapping.json` | `mapping > rag-docs > mappings > properties > embedding > dims` |  | 1 |
| text-embedding-3-small | `eval/results/retrieval_baseline.json` | `meta > settings > embed_model` |  | 1 |
| bbq_hnsw | `eval/results/mapping.json` | `mapping > rag-docs > mappings > properties > embedding > index_options > type` | effective index_options | 3 |
| title^2 | `eval/results/retrieval_baseline.json` | `meta > settings > bm25_fields[0]` | BM25 field boost | 1 |
| heading_path^1.5 | `eval/results/retrieval_baseline.json` | `meta > settings > bm25_fields[1]` | BM25 field boost | 1 |
| content | `eval/results/retrieval_baseline.json` | `meta > settings > bm25_fields[2]` | BM25 field boost | 1 |
| 60 | `eval/results/retrieval_baseline.json` | `meta > settings > rrf_k` |  | 2 |
| 200 | `eval/results/retrieval_baseline.json` | `meta > settings > pool` |  | 3 |
| 8 | `eval/results/answer_eval.json` | `meta > context > max_chunks` |  | 2 |
| 2 | `eval/results/answer_eval.json` | `meta > context > per_doc` |  | 2 |
| claude-sonnet-5-5 | `eval/results/answer_eval.json` | `meta > answer_model` |  | 2 |
| claude-haiku-5-5 | `eval/results/answer_eval.json` | `meta > verifier_model` |  | 2 |
| claims-v2 | `eval/results/answer_eval.json` | `meta > rubric` |  | 1 |
| 8 | `eval/results/retrieval_baseline.json` | `meta > n_by_type > exact_term` |  | 3 |
| 8 | `eval/results/retrieval_baseline.json` | `meta > n_by_type > mixed` |  | 3 |
| 10 | `eval/results/retrieval_baseline.json` | `meta > n_by_type > conceptual` |  | 4 |
| 16 | `eval/results/bare_term.json` | `results > heading/bm25 > overall > n` |  | 4 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > fixed/bm25 > slices > exact_term > recall@10` |  | 1 |
| 0.875 | `eval/results/robustness_summary.json` | `rows > fixed/bm25 > slices > exact_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > fixed/bm25 > slices > mixed > recall@10` |  | 1 |
| 0.889 | `eval/results/robustness_summary.json` | `rows > fixed/bm25 > slices > mixed > mrr` |  | 1 |
| 0.000 | `eval/results/robustness_summary.json` | `rows > fixed/bm25 > slices > conceptual > recall@10` |  | 2 |
| 0.028 | `eval/results/robustness_summary.json` | `rows > fixed/bm25 > slices > conceptual > mrr` |  | 1 |
| 0.938 | `eval/results/robustness_summary.json` | `rows > fixed/bm25 > slices > bare_term > recall@10` |  | 1 |
| 0.651 | `eval/results/robustness_summary.json` | `rows > fixed/bm25 > slices > bare_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > fixed/dense > slices > exact_term > recall@10` |  | 1 |
| 0.854 | `eval/results/robustness_summary.json` | `rows > fixed/dense > slices > exact_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > fixed/dense > slices > mixed > recall@10` |  | 1 |
| 0.838 | `eval/results/robustness_summary.json` | `rows > fixed/dense > slices > mixed > mrr` |  | 1 |
| 0.650 | `eval/results/robustness_summary.json` | `rows > fixed/dense > slices > conceptual > recall@10` |  | 2 |
| 0.347 | `eval/results/robustness_summary.json` | `rows > fixed/dense > slices > conceptual > mrr` |  | 1 |
| 0.656 | `eval/results/robustness_summary.json` | `rows > fixed/dense > slices > bare_term > recall@10` |  | 2 |
| 0.331 | `eval/results/robustness_summary.json` | `rows > fixed/dense > slices > bare_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > fixed/hybrid > slices > exact_term > recall@10` |  | 1 |
| 0.938 | `eval/results/robustness_summary.json` | `rows > fixed/hybrid > slices > exact_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > fixed/hybrid > slices > mixed > recall@10` |  | 1 |
| 0.854 | `eval/results/robustness_summary.json` | `rows > fixed/hybrid > slices > mixed > mrr` |  | 1 |
| 0.450 | `eval/results/robustness_summary.json` | `rows > fixed/hybrid > slices > conceptual > recall@10` |  | 2 |
| 0.129 | `eval/results/robustness_summary.json` | `rows > fixed/hybrid > slices > conceptual > mrr` |  | 1 |
| 0.938 | `eval/results/robustness_summary.json` | `rows > fixed/hybrid > slices > bare_term > recall@10` |  | 2 |
| 0.487 | `eval/results/robustness_summary.json` | `rows > fixed/hybrid > slices > bare_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > heading/bm25 > slices > exact_term > recall@10` |  | 1 |
| 0.854 | `eval/results/robustness_summary.json` | `rows > heading/bm25 > slices > exact_term > mrr` |  | 1 |
| 0.875 | `eval/results/robustness_summary.json` | `rows > heading/bm25 > slices > mixed > recall@10` |  | 1 |
| 0.760 | `eval/results/robustness_summary.json` | `rows > heading/bm25 > slices > mixed > mrr` |  | 1 |
| 0.250 | `eval/results/robustness_summary.json` | `rows > heading/bm25 > slices > conceptual > recall@10` |  | 2 |
| 0.072 | `eval/results/robustness_summary.json` | `rows > heading/bm25 > slices > conceptual > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > heading/bm25 > slices > bare_term > recall@10` |  | 1 |
| 0.619 | `eval/results/robustness_summary.json` | `rows > heading/bm25 > slices > bare_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > heading/dense > slices > exact_term > recall@10` |  | 1 |
| 0.729 | `eval/results/robustness_summary.json` | `rows > heading/dense > slices > exact_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > heading/dense > slices > mixed > recall@10` |  | 1 |
| 0.826 | `eval/results/robustness_summary.json` | `rows > heading/dense > slices > mixed > mrr` |  | 1 |
| 0.683 | `eval/results/robustness_summary.json` | `rows > heading/dense > slices > conceptual > recall@10` |  | 2 |
| 0.393 | `eval/results/robustness_summary.json` | `rows > heading/dense > slices > conceptual > mrr` |  | 1 |
| 0.719 | `eval/results/robustness_summary.json` | `rows > heading/dense > slices > bare_term > recall@10` |  | 2 |
| 0.344 | `eval/results/robustness_summary.json` | `rows > heading/dense > slices > bare_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > heading/hybrid > slices > exact_term > recall@10` |  | 1 |
| 0.875 | `eval/results/robustness_summary.json` | `rows > heading/hybrid > slices > exact_term > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > heading/hybrid > slices > mixed > recall@10` |  | 1 |
| 0.906 | `eval/results/robustness_summary.json` | `rows > heading/hybrid > slices > mixed > mrr` |  | 1 |
| 0.550 | `eval/results/robustness_summary.json` | `rows > heading/hybrid > slices > conceptual > recall@10` |  | 2 |
| 0.240 | `eval/results/robustness_summary.json` | `rows > heading/hybrid > slices > conceptual > mrr` |  | 1 |
| 1.000 | `eval/results/robustness_summary.json` | `rows > heading/hybrid > slices > bare_term > recall@10` |  | 2 |
| 0.610 | `eval/results/robustness_summary.json` | `rows > heading/hybrid > slices > bare_term > mrr` |  | 1 |
| 0.878 | `eval/results/retrieval_baseline.json` | `results > heading/dense > overall > recall@10` |  | 3 |
| 0.827 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > overall > recall@10` |  | 3 |
| 7 | `eval/results/retrieval_baseline.json` | `paired > heading: hybrid vs dense > overall > win` |  | 1 |
| 12 | `eval/results/retrieval_baseline.json` | `paired > heading: hybrid vs dense > overall > tie` |  | 1 |
| 7 | `eval/results/retrieval_baseline.json` | `paired > heading: hybrid vs dense > overall > loss` |  | 1 |
| 2 | `eval/results/retrieval_baseline.json` | `paired > heading: hybrid vs dense > conceptual > win` |  | 1 |
| 1 | `eval/results/retrieval_baseline.json` | `paired > heading: hybrid vs dense > conceptual > tie` |  | 1 |
| 7 | `eval/results/retrieval_baseline.json` | `paired > heading: hybrid vs dense > conceptual > loss` |  | 1 |
| 9 | `eval/results/bare_term.json` | `results > heading/bm25 > overall > exhausted` |  | 1 |
| 0 | `eval/results/bare_term.json` | `results > heading/bm25 > overall > exhausted_missed` |  | 1 |
| 16 | `eval/results/bare_term.json` | `results > fixed/bm25 > overall > n` |  | 1 |
| 0.938 | `eval/results/bare_term.json` | `results > fixed/bm25 > overall > recall@10` |  | 1 |
| 0.812-1.000 | `eval/results/bare_term.json` | `results > fixed/bm25 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.651 | `eval/results/bare_term.json` | `results > fixed/bm25 > overall > mrr` |  | 2 |
| 0.474-0.823 | `eval/results/bare_term.json` | `results > fixed/bm25 > overall > mrr_ci95` | 95% CI | 1 |
| 16 | `eval/results/bare_term.json` | `results > fixed/dense > overall > n` |  | 1 |
| 0.656 | `eval/results/bare_term.json` | `results > fixed/dense > overall > recall@10` |  | 1 |
| 0.438-0.875 | `eval/results/bare_term.json` | `results > fixed/dense > overall > recall@10_ci95` | 95% CI | 1 |
| 0.331 | `eval/results/bare_term.json` | `results > fixed/dense > overall > mrr` |  | 1 |
| 0.172-0.511 | `eval/results/bare_term.json` | `results > fixed/dense > overall > mrr_ci95` | 95% CI | 1 |
| 16 | `eval/results/bare_term.json` | `results > fixed/hybrid > overall > n` |  | 1 |
| 0.938 | `eval/results/bare_term.json` | `results > fixed/hybrid > overall > recall@10` |  | 1 |
| 0.812-1.000 | `eval/results/bare_term.json` | `results > fixed/hybrid > overall > recall@10_ci95` | 95% CI | 1 |
| 0.487 | `eval/results/bare_term.json` | `results > fixed/hybrid > overall > mrr` |  | 2 |
| 0.340-0.651 | `eval/results/bare_term.json` | `results > fixed/hybrid > overall > mrr_ci95` | 95% CI | 1 |
| 1.000 | `eval/results/bare_term.json` | `results > heading/bm25 > overall > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/bare_term.json` | `results > heading/bm25 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.619 | `eval/results/bare_term.json` | `results > heading/bm25 > overall > mrr` |  | 2 |
| 0.451-0.792 | `eval/results/bare_term.json` | `results > heading/bm25 > overall > mrr_ci95` | 95% CI | 1 |
| 16 | `eval/results/bare_term.json` | `results > heading/dense > overall > n` |  | 1 |
| 0.719 | `eval/results/bare_term.json` | `results > heading/dense > overall > recall@10` |  | 1 |
| 0.500-0.906 | `eval/results/bare_term.json` | `results > heading/dense > overall > recall@10_ci95` | 95% CI | 1 |
| 0.344 | `eval/results/bare_term.json` | `results > heading/dense > overall > mrr` |  | 1 |
| 0.187-0.525 | `eval/results/bare_term.json` | `results > heading/dense > overall > mrr_ci95` | 95% CI | 1 |
| 16 | `eval/results/bare_term.json` | `results > heading/hybrid > overall > n` |  | 1 |
| 1.000 | `eval/results/bare_term.json` | `results > heading/hybrid > overall > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/bare_term.json` | `results > heading/hybrid > overall > recall@10_ci95` | 95% CI | 1 |
| 0.610 | `eval/results/bare_term.json` | `results > heading/hybrid > overall > mrr` |  | 2 |
| 0.440-0.786 | `eval/results/bare_term.json` | `results > heading/hybrid > overall > mrr_ci95` | 95% CI | 1 |
| 30 | `eval/results/answer_eval.json` | `configs > heading/hybrid > summary > n_questions` |  | 2 |
| 4 | `eval/results/retrieval_baseline.json` | `meta > n_unanswerable` |  | 1 |
| 10,000 | `eval/results/retrieval_baseline.json` | `meta > settings > bootstrap > n` |  | 1 |
| 200 | `eval/results/retrieval_baseline.json` | `meta > settings > knn > k` |  | 1 |
| 800 | `eval/results/retrieval_baseline.json` | `meta > settings > knn > num_candidates` |  | 1 |
| 26 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > overall > n` |  | 1 |
| 0.577 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > overall > recall@5` |  | 1 |
| 0.615 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > overall > recall@10` |  | 1 |
| 0.423-0.808 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.554 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > overall > mrr` |  | 1 |
| 0.372-0.735 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > overall > mrr_ci95` | 95% CI | 1 |
| 26 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > overall > n` |  | 1 |
| 0.821 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > overall > recall@5` |  | 1 |
| 0.865 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > overall > recall@10` |  | 2 |
| 0.731-0.981 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > overall > recall@10_ci95` | 95% CI | 1 |
| 0.654 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > overall > mrr` |  | 1 |
| 0.499-0.804 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > overall > mrr_ci95` | 95% CI | 1 |
| 26 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > overall > n` |  | 1 |
| 0.731 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > overall > recall@5` |  | 1 |
| 0.788 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > overall > recall@10` |  | 2 |
| 0.635-0.923 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > overall > recall@10_ci95` | 95% CI | 1 |
| 0.601 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > overall > mrr` |  | 1 |
| 0.441-0.764 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > overall > mrr_ci95` | 95% CI | 1 |
| 26 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > overall > n` |  | 1 |
| 0.635 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > overall > recall@5` |  | 1 |
| 0.673 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > overall > recall@10` |  | 1 |
| 0.500-0.846 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.524 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > overall > mrr` |  | 1 |
| 0.358-0.693 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > overall > mrr_ci95` | 95% CI | 1 |
| 26 | `eval/results/retrieval_baseline.json` | `results > heading/dense > overall > n` |  | 1 |
| 0.769 | `eval/results/retrieval_baseline.json` | `results > heading/dense > overall > recall@5` |  | 1 |
| 0.750-0.981 | `eval/results/retrieval_baseline.json` | `results > heading/dense > overall > recall@10_ci95` | 95% CI | 1 |
| 0.630 | `eval/results/retrieval_baseline.json` | `results > heading/dense > overall > mrr` |  | 1 |
| 0.489-0.772 | `eval/results/retrieval_baseline.json` | `results > heading/dense > overall > mrr_ci95` | 95% CI | 1 |
| 0.788 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > overall > recall@5` |  | 1 |
| 0.692-0.962 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > overall > recall@10_ci95` | 95% CI | 1 |
| 0.640 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > overall > mrr` |  | 1 |
| 0.488-0.795 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > overall > mrr_ci95` | 95% CI | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > by_type > exact_term > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > by_type > exact_term > recall@10_ci95` | 95% CI | 1 |
| 0.88 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > by_type > exact_term > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > by_type > mixed > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > by_type > mixed > recall@10_ci95` | 95% CI | 1 |
| 0.89 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > by_type > mixed > mrr` |  | 1 |
| 0.00 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > by_type > conceptual > recall@10` |  | 1 |
| 0.000-0.000 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > by_type > conceptual > recall@10_ci95` | 95% CI | 1 |
| 0.03 | `eval/results/retrieval_baseline.json` | `results > fixed/bm25 > by_type > conceptual > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > by_type > exact_term > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > by_type > exact_term > recall@10_ci95` | 95% CI | 1 |
| 0.85 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > by_type > exact_term > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > by_type > mixed > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > by_type > mixed > recall@10_ci95` | 95% CI | 1 |
| 0.84 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > by_type > mixed > mrr` |  | 1 |
| 0.65 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > by_type > conceptual > recall@10` |  | 1 |
| 0.350-0.900 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > by_type > conceptual > recall@10_ci95` | 95% CI | 1 |
| 0.35 | `eval/results/retrieval_baseline.json` | `results > fixed/dense > by_type > conceptual > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > by_type > exact_term > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > by_type > exact_term > recall@10_ci95` | 95% CI | 1 |
| 0.94 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > by_type > exact_term > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > by_type > mixed > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > by_type > mixed > recall@10_ci95` | 95% CI | 1 |
| 0.85 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > by_type > mixed > mrr` |  | 1 |
| 0.45 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > by_type > conceptual > recall@10` |  | 1 |
| 0.200-0.750 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > by_type > conceptual > recall@10_ci95` | 95% CI | 1 |
| 0.13 | `eval/results/retrieval_baseline.json` | `results > fixed/hybrid > by_type > conceptual > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > by_type > exact_term > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > by_type > exact_term > recall@10_ci95` | 95% CI | 1 |
| 0.85 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > by_type > exact_term > mrr` |  | 1 |
| 0.88 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > by_type > mixed > recall@10` |  | 1 |
| 0.625-1.000 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > by_type > mixed > recall@10_ci95` | 95% CI | 1 |
| 0.76 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > by_type > mixed > mrr` |  | 1 |
| 0.25 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > by_type > conceptual > recall@10` |  | 1 |
| 0.000-0.500 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > by_type > conceptual > recall@10_ci95` | 95% CI | 1 |
| 0.07 | `eval/results/retrieval_baseline.json` | `results > heading/bm25 > by_type > conceptual > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > heading/dense > by_type > exact_term > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > heading/dense > by_type > exact_term > recall@10_ci95` | 95% CI | 1 |
| 0.73 | `eval/results/retrieval_baseline.json` | `results > heading/dense > by_type > exact_term > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > heading/dense > by_type > mixed > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > heading/dense > by_type > mixed > recall@10_ci95` | 95% CI | 1 |
| 0.83 | `eval/results/retrieval_baseline.json` | `results > heading/dense > by_type > mixed > mrr` |  | 1 |
| 0.68 | `eval/results/retrieval_baseline.json` | `results > heading/dense > by_type > conceptual > recall@10` |  | 1 |
| 0.433-0.933 | `eval/results/retrieval_baseline.json` | `results > heading/dense > by_type > conceptual > recall@10_ci95` | 95% CI | 1 |
| 0.39 | `eval/results/retrieval_baseline.json` | `results > heading/dense > by_type > conceptual > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > by_type > exact_term > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > by_type > exact_term > recall@10_ci95` | 95% CI | 1 |
| 0.88 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > by_type > exact_term > mrr` |  | 1 |
| 1.00 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > by_type > mixed > recall@10` |  | 1 |
| 1.000-1.000 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > by_type > mixed > recall@10_ci95` | 95% CI | 1 |
| 0.91 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > by_type > mixed > mrr` |  | 1 |
| 0.55 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > by_type > conceptual > recall@10` |  | 1 |
| 0.250-0.850 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > by_type > conceptual > recall@10_ci95` | 95% CI | 1 |
| 0.24 | `eval/results/retrieval_baseline.json` | `results > heading/hybrid > by_type > conceptual > mrr` |  | 1 |
| 26 | `eval/results/rrf_weights.json` | `results > fixed/dense > overall > n` |  | 1 |
| 0.865 | `eval/results/rrf_weights.json` | `results > fixed/dense > overall > recall@10` |  | 1 |
| 0.731-0.981 | `eval/results/rrf_weights.json` | `results > fixed/dense > overall > recall@10_ci95` | 95% CI | 1 |
| 0.65 | `eval/results/rrf_weights.json` | `results > fixed/dense > by_type > conceptual > recall@10` |  | 1 |
| fixed/hybrid w1 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1` | row label (key name) | 1 |
| 26 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1 > overall > n` |  | 1 |
| 0.788 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1 > overall > recall@10` |  | 1 |
| 0.635-0.923 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.45 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1 > by_type > conceptual > recall@10` |  | 1 |
| fixed/hybrid w1.5 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1.5` | row label (key name) | 1 |
| 26 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1.5 > overall > n` |  | 1 |
| 0.821 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1.5 > overall > recall@10` |  | 1 |
| 0.667-0.962 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1.5 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.53 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w1.5 > by_type > conceptual > recall@10` |  | 1 |
| fixed/hybrid w2 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w2` | row label (key name) | 1 |
| 26 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w2 > overall > n` |  | 1 |
| 0.821 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w2 > overall > recall@10` |  | 1 |
| 0.667-0.962 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w2 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.53 | `eval/results/rrf_weights.json` | `results > fixed/hybrid w2 > by_type > conceptual > recall@10` |  | 1 |
| 26 | `eval/results/rrf_weights.json` | `results > heading/dense > overall > n` |  | 1 |
| 0.878 | `eval/results/rrf_weights.json` | `results > heading/dense > overall > recall@10` |  | 1 |
| 0.750-0.981 | `eval/results/rrf_weights.json` | `results > heading/dense > overall > recall@10_ci95` | 95% CI | 1 |
| 0.68 | `eval/results/rrf_weights.json` | `results > heading/dense > by_type > conceptual > recall@10` |  | 1 |
| heading/hybrid w1 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1` | row label (key name) | 1 |
| 26 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1 > overall > n` |  | 1 |
| 0.827 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1 > overall > recall@10` |  | 1 |
| 0.692-0.962 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.55 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1 > by_type > conceptual > recall@10` |  | 1 |
| heading/hybrid w1.5 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1.5` | row label (key name) | 1 |
| 26 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1.5 > overall > n` |  | 1 |
| 0.865 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1.5 > overall > recall@10` |  | 1 |
| 0.731-0.981 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1.5 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.65 | `eval/results/rrf_weights.json` | `results > heading/hybrid w1.5 > by_type > conceptual > recall@10` |  | 1 |
| heading/hybrid w2 | `eval/results/rrf_weights.json` | `results > heading/hybrid w2` | row label (key name) | 1 |
| 26 | `eval/results/rrf_weights.json` | `results > heading/hybrid w2 > overall > n` |  | 1 |
| 0.865 | `eval/results/rrf_weights.json` | `results > heading/hybrid w2 > overall > recall@10` |  | 1 |
| 0.731-0.981 | `eval/results/rrf_weights.json` | `results > heading/hybrid w2 > overall > recall@10_ci95` | 95% CI | 1 |
| 0.65 | `eval/results/rrf_weights.json` | `results > heading/hybrid w2 > by_type > conceptual > recall@10` |  | 1 |
| 0.865 | `eval/results/index_options.json` | `results > fixed/dense [bbq_hnsw] > overall > recall@10` |  | 1 |
| 0.865 | `eval/results/index_options.json` | `results > fixed/dense [hnsw] > overall > recall@10` |  | 1 |
| 0.788 | `eval/results/index_options.json` | `results > fixed/hybrid [bbq_hnsw] > overall > recall@10` |  | 1 |
| 0.788 | `eval/results/index_options.json` | `results > fixed/hybrid [hnsw] > overall > recall@10` |  | 1 |
| 0.878 | `eval/results/index_options.json` | `results > heading/dense [bbq_hnsw] > overall > recall@10` |  | 1 |
| 0.878 | `eval/results/index_options.json` | `results > heading/dense [hnsw] > overall > recall@10` |  | 1 |
| 0.827 | `eval/results/index_options.json` | `results > heading/hybrid [bbq_hnsw] > overall > recall@10` |  | 1 |
| 0.827 | `eval/results/index_options.json` | `results > heading/hybrid [hnsw] > overall > recall@10` |  | 1 |
| 0.808 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > answer_coverage > value` |  | 1 |
| 0.654-0.962 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > answer_coverage > ci95` | 95% CI | 1 |
| 5 | `eval/results/answer_eval.json` | `configs > heading/hybrid > summary > false_refusals` |  | 2 |
| 4 | `eval/results/answer_eval.json` | `configs > heading/hybrid > summary > correct_refusals` |  | 2 |
| 4 | `eval/results/answer_eval.json` | `configs > heading/hybrid > summary > n_unanswerable` |  | 4 |
| 0 | `eval/results/answer_eval.json` | `configs > heading/hybrid > summary > answered_unanswerable` |  | 2 |
| 0.962 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > faithfulness_strict > value` |  | 1 |
| 0.924-1.000 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > faithfulness_strict > ci95` | 95% CI | 1 |
| 78 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > faithfulness_strict > denominator` |  | 1 |
| 21 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > faithfulness_strict > units` |  | 1 |
| 1.000 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > faithfulness_lenient > value` |  | 1 |
| 0.917 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > citation_precision > value` |  | 1 |
| 0.864-0.974 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > citation_precision > ci95` | 95% CI | 1 |
| 84 | `eval/results/answer_eval.json` | `configs > heading/hybrid > ci > citation_precision > denominator` |  | 1 |
| 0.885 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > answer_coverage > value` |  | 1 |
| 0.731-1.000 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > answer_coverage > ci95` | 95% CI | 1 |
| 3 | `eval/results/answer_eval.json` | `configs > heading/dense > summary > false_refusals` |  | 2 |
| 4 | `eval/results/answer_eval.json` | `configs > heading/dense > summary > correct_refusals` |  | 1 |
| 4 | `eval/results/answer_eval.json` | `configs > heading/dense > summary > n_unanswerable` |  | 1 |
| 0 | `eval/results/answer_eval.json` | `configs > heading/dense > summary > answered_unanswerable` |  | 1 |
| 0.961 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > faithfulness_strict > value` |  | 1 |
| 0.912-1.000 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > faithfulness_strict > ci95` | 95% CI | 1 |
| 77 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > faithfulness_strict > denominator` |  | 1 |
| 23 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > faithfulness_strict > units` |  | 1 |
| 1.000 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > faithfulness_lenient > value` |  | 1 |
| 0.951 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > citation_precision > value` |  | 1 |
| 0.887-1.000 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > citation_precision > ci95` | 95% CI | 1 |
| 81 | `eval/results/answer_eval.json` | `configs > heading/dense > ci > citation_precision > denominator` |  | 1 |
| 21 of 26 | `eval/results/answer_eval.json` | `configs > heading/hybrid > summary > context_has_expected` |  | 1 |
| 22 of 26 | `eval/results/answer_eval.json` | `configs > heading/dense > summary > context_has_expected` |  | 1 |
| 20 | `eval/results/answer_eval.json` | `paired_hybrid_vs_dense > answerable_26 > outcomes > both_answered` |  | 1 |
| 1 | `eval/results/answer_eval.json` | `paired_hybrid_vs_dense > answerable_26 > outcomes > only_hybrid_answered` |  | 1 |
| 3 | `eval/results/answer_eval.json` | `paired_hybrid_vs_dense > answerable_26 > outcomes > only_dense_answered` |  | 1 |
| 2 | `eval/results/answer_eval.json` | `paired_hybrid_vs_dense > answerable_26 > outcomes > both_refused` |  | 1 |
| 2 | `eval/results/answer_eval.json` | `paired_hybrid_vs_dense > answerable_26 > faithfulness_both_verified > win` |  | 1 |
| 16 | `eval/results/answer_eval.json` | `paired_hybrid_vs_dense > answerable_26 > faithfulness_both_verified > tie` |  | 1 |
| 2 | `eval/results/answer_eval.json` | `paired_hybrid_vs_dense > answerable_26 > faithfulness_both_verified > loss` |  | 1 |
| 26 | `eval/results/native_rrf_check.json` | `summary > fixed > n` |  | 1 |
| 367 | `eval/results/chunk_stats.json` | `fixed > tokens_median` |  | 1 |
| 245 | `eval/results/chunk_stats.json` | `heading > tokens_median` |  | 1 |
| 649 | `eval/results/chunk_stats.json` | `heading > tokens_max` |  | 1 |
| 281 | `eval/results/chunk_stats.json` | `whats_next_sections_removed` |  | 1 |
| 30,606 | `eval/results/chunk_stats.json` | `whats_next_tokens_removed` |  | 1 |
| 1,281 | `eval/results/chunk_stats.json` | `entities_decoded` |  | 1 |
| $0.7295 | `eval/results/answer_eval.json` | `meta > run_cost_usd_reported` |  | 1 |
| 25 | `eval/results/verify_mutation_haiku.json` | `n` |  | 1 |
| 10 | `eval/results/verify_mutation_haiku.json` | `summary > wrong_pairs > no` |  | 1 |
| 10 | `eval/results/verify_mutation_haiku.json` | `summary > wrong_pairs > n` |  | 1 |
| 5 | `eval/results/verify_mutation_haiku.json` | `summary > controls_verbatim > yes` |  | 1 |
| 5 | `eval/results/verify_mutation_haiku.json` | `summary > controls_verbatim > n` |  | 1 |
| 10 | `eval/results/verify_mutation_haiku.json` | `summary > controls_paraphrase > yes` |  | 1 |
| 10 | `eval/results/verify_mutation_haiku.json` | `summary > controls_paraphrase > n` |  | 1 |
| 0.635 | `eval/results/golden_overlap.json` | `by_type > conceptual > ratio_median` |  | 1 |
| 0.865 | `eval/results/golden_overlap.json` | `by_type > exact_term > ratio_median` |  | 1 |
| 0.6 | `eval/results/golden_overlap.json` | `by_type > conceptual > rare_terms_mean` |  | 1 |
| 0 | `eval/results/golden_overlap.json` | `by_type > conceptual > copied_phrase` |  | 1 |
| 0.794-1.000 | `computed here` | `Clopper-Pearson, n=16, every question a hit` | exact 95% interval (computed) | 2 |
| 0.631-1.000 | `computed here` | `Clopper-Pearson, n=8, every question a hit` | exact 95% interval (computed) | 11 |
| 0.000-0.308 | `computed here` | `Clopper-Pearson, n=10, every question a miss` | exact 95% interval (computed) | 1 |
| 21 of 26 | `eval/results/answer_eval.json` | `configs > heading/hybrid > summary > n_answerable - false_refusals` | answered answerable questions (computed) | 1 |
| 23 of 26 | `eval/results/answer_eval.json` | `configs > heading/dense > summary > n_answerable - false_refusals` | answered answerable questions (computed) | 1 |
| 0.40 | `computed here` | `0.025 ** (1/4)` | exact 95% lower bound for 4 of 4 refusals (computed) | 1 |
| 2026-11-22 | `eval/results/native_rrf_check.json` | `meta > license > expiry (date part)` | trial expiry (computed) | 1 |
| 52 | `eval/results/native_rrf_check.json` | `summary > fixed + heading > first_rank_identical` | sum over both chunkers (computed) | 1 |
| 52 | `eval/results/native_rrf_check.json` | `summary > fixed + heading > n` | sum over both chunkers (computed) | 2 |
| 48 | `eval/results/native_rrf_check.json` | `summary > fixed + heading > top10_chunks_identical_order` | sum over both chunkers (computed) | 1 |
| 44 | `eval/results/answer_eval_generation.jsonl + answer_eval_verification.jsonl` | `questions with a verification record` | answered questions (both configs) (computed) | 1 |
| $0.0076 | `eval/results/answer_eval_generation.jsonl + answer_eval_verification.jsonl` | `min(generation + verification cost_usd)` | per-answered-question cost (computed) | 1 |
| $0.0190 | `eval/results/answer_eval_generation.jsonl + answer_eval_verification.jsonl` | `max(generation + verification cost_usd)` | per-answered-question cost (computed) | 1 |
| $0.0131 | `eval/results/answer_eval_generation.jsonl + answer_eval_verification.jsonl` | `median(generation + verification cost_usd)` | per-answered-question cost (computed) | 1 |
| 16 | `eval/results/answer_eval_generation.jsonl + answer_eval_verification.jsonl` | `questions without a verification record` | refused questions (both configs) (computed) | 1 |
| $0.0057 | `eval/results/answer_eval_generation.jsonl + answer_eval_verification.jsonl` | `min(generation cost_usd)` | refusal cost (computed) | 1 |
| $0.0136 | `eval/results/answer_eval_generation.jsonl + answer_eval_verification.jsonl` | `max(generation cost_usd)` | refusal cost (computed) | 1 |
| $0.7296 | `eval/results/answer_eval_generation.jsonl + answer_eval_verification.jsonl` | `sum of all cost_usd in both logs` | answer-eval total from logs (computed) | 1 |

## 2. From prose docs (not machine-read from result files)

| value | source | note | uses |
|---|---|---|---|
| 9 | docs/CORPUS.md | headless include partials excluded (regex-read) | 1 |
| $0.0173 | NOTES.md Phase 8 step 2 | one live /ask, answerable, 12 sentences | 1 |
| $0.053 | NOTES.md Phase 8 step 2 | worst-case estimate for one /ask | 1 |
| $0.0103 | NOTES.md Phase 8 step 2 | one live /ask refusal | 1 |
| about $1.1 | STATUS.md 'Spend so far' | whole-project API spend; the ledger's 1.0776 excludes the clean-clone embedding (0.0534) | 1 |
| 1.0776 | STATUS.md / NOTES.md Phase 8 step 2 | spend-ledger value after the live API calls | 1 |
| $0.0534 | eval/results/clean_clone_check.md; STATUS.md | clean-clone embedding, run from the host | 1 |
| The verifier was not validated against human judgement: hand labelling... | STATUS.md 'README limitations' (copied verbatim) | limitation text | 1 |
| Answers were compared with the reference answers by an automated judge... | STATUS.md 'README limitations' (copied verbatim) | limitation text | 1 |
| the verifier mutation set is a dev set built from the verifier's own e... | STATUS.md 'README limitations' (copied verbatim) | limitation text | 1 |
| 1 of 104 | eval/results/clean_clone_check.md | dense/hybrid first ranks moved in the clean clone | 1 |
| 6c42e266fcc1f0e0edd4805baea904e1b3cbaf9c | docs/CORPUS.md | pinned corpus commit (regex-read by this script) | 1 |

## 3. Typed constants (configuration or description, with where each is stated)

| text | meaning | stated in | uses |
|---|---|---|---|
| 400 | fixed chunker target tokens | docs/BUILD_GUIDE.md Phase 1 | 1 |
| 1.000 | Recall@10 value at which the bootstrap interval degenerates | definition in the note below the bare-term table | 1 |
| 0.000 | Recall@10 value at which the bootstrap interval degenerates | definition in the note below the bare-term table | 1 |
| 1 / 1.5 / 2 | dense weights tried (BM25 weight 1) | eval/results/rrf_weights.md | 1 |
| 1 | BM25 weight | eval/results/rrf_weights.md | 1 |
| c009, c010, c002 | golden question ids | eval/results/failure_analysis.md | 1 |
| 403 | HTTP status of the Enterprise-gated rrf retriever on a Basic licence | docs/BUILD_GUIDE.md licence section | 1 |
| 30 | days of the trial licence | docs/BUILD_GUIDE.md licence section | 1 |
| 2 | two chunkers | docs/BUILD_GUIDE.md | 1 |
| 10 | top-10 list in the native-vs-Python comparison | eval/results/native_rrf_check.md | 1 |
| 1 | human labelling round that had no controls | STATUS.md 'Checkpoint 4: CLOSED' | 1 |
| 2 and 3 | human labelling rounds that failed their pre-registered controls | STATUS.md 'Checkpoint 4: CLOSED' | 1 |
| $0.05 | approximate paid embedding step | docs/SETUP.md cost table | 1 |
| 4.0 | CC BY licence version | docs/CORPUS.md | 2 |
| 50 | reranker candidate depth (a proposal, not a result) | docs/BUILD_GUIDE.md Stretch | 1 |
