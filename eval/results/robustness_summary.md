# Robustness summary

Built from saved results only (no runs). Each cell is Recall@10 / MRR with the slice size n. exact_term, mixed and conceptual are the baseline slices of the golden set; bare_term is the diagnostic that queries the exact term alone for the 16 exact_term and mixed questions (same expected docs). Worst slice = lowest Recall@10, ties broken by lower MRR. n is small (8 / 8 / 10 / 16); read gaps with care.

## Baseline rows

| row | exact_term R@10 / MRR (n) | mixed R@10 / MRR (n) | conceptual R@10 / MRR (n) | bare_term R@10 / MRR (n) | worst slice |
|---|---|---|---|---|---|
| fixed/bm25 | 1.000 / 0.875 (8) | 1.000 / 0.889 (8) | 0.000 / 0.028 (10) | 0.938 / 0.651 (16) | conceptual |
| fixed/dense | 1.000 / 0.854 (8) | 1.000 / 0.838 (8) | 0.650 / 0.347 (10) | 0.656 / 0.331 (16) | conceptual |
| fixed/hybrid | 1.000 / 0.938 (8) | 1.000 / 0.854 (8) | 0.450 / 0.129 (10) | 0.938 / 0.487 (16) | conceptual |
| heading/bm25 | 1.000 / 0.854 (8) | 0.875 / 0.760 (8) | 0.250 / 0.072 (10) | 1.000 / 0.619 (16) | conceptual |
| heading/dense | 1.000 / 0.729 (8) | 1.000 / 0.826 (8) | 0.683 / 0.393 (10) | 0.719 / 0.344 (16) | conceptual |
| heading/hybrid | 1.000 / 0.875 (8) | 1.000 / 0.906 (8) | 0.550 / 0.240 (10) | 1.000 / 0.610 (16) | conceptual |

## Weighted-RRF hybrid rows (sensitivity, not tuning; no weight is chosen)

Dense weight 1 / 1.5 / 2 with BM25 weight 1; weight 1 is the baseline fusion. No bare_term slice (the diagnostic was not run with weights).

| row | exact_term R@10 / MRR (n) | mixed R@10 / MRR (n) | conceptual R@10 / MRR (n) | worst slice |
|---|---|---|---|---|
| fixed/hybrid w1 | 1.000 / 0.938 (8) | 1.000 / 0.854 (8) | 0.450 / 0.129 (10) | conceptual |
| heading/hybrid w1 | 1.000 / 0.875 (8) | 1.000 / 0.906 (8) | 0.550 / 0.240 (10) | conceptual |
| fixed/hybrid w1.5 | 1.000 / 0.938 (8) | 1.000 / 0.875 (8) | 0.533 / 0.180 (10) | conceptual |
| heading/hybrid w1.5 | 1.000 / 0.875 (8) | 1.000 / 0.900 (8) | 0.650 / 0.285 (10) | conceptual |
| fixed/hybrid w2 | 1.000 / 0.938 (8) | 1.000 / 0.875 (8) | 0.533 / 0.236 (10) | conceptual |
| heading/hybrid w2 | 1.000 / 0.854 (8) | 1.000 / 0.900 (8) | 0.650 / 0.288 (10) | conceptual |
