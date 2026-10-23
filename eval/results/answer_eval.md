# Answer eval

Git `b874349` | 2026-10-23T05:29:02+00:00 | answers `claude-sonnet-5-5` (effort medium), verifier `claude-haiku-5-5` (claims-v2, effort low) | run cost $0.7295 (spend guard; the logs sum to slightly less, see NOTES.md)

**Answer coverage** = answered share of the 26 answerable questions; **context coverage** = share whose 8-chunk context holds an expected doc. Faithfulness is only measured on answered questions, so read it together with answer coverage. Strict = sentences with at least one cited excerpt judged yes; lenient = yes or partial; citation precision = share of cited pairs judged yes. Intervals are 95% bootstrap (10,000 resamples of questions, seed 0); n is small. The verifier is unvalidated until the checkpoint-4 hand labels. Faithfulness is support by the cited excerpts, not correctness against the reference.

## Per config

| metric | heading/hybrid | heading/dense |
|---|---|---|
| answer coverage (answered / 26) | 0.808 (0.65-0.96) | 0.885 (0.73-1.00) |
| false-refusal rate (of 26) | 0.192 (0.04-0.35) | 0.115 (0.00-0.27) |
| context coverage (expected doc in context, of 26) | 0.808 (0.65-0.96) | 0.846 (0.69-0.96) |
| faithfulness strict | 0.962 (0.92-1.00) | 0.961 (0.91-1.00) |
| faithfulness lenient | 1.000 (1.00-1.00) | 1.000 (1.00-1.00) |
| citation precision | 0.917 (0.86-0.97) | 0.951 (0.89-1.00) |
| sentences scored / verified answers | 78 / 21 | 77 / 23 |
| correct refusals (of 4) / answered unanswerable | 4 / 0 | 4 / 0 |
| invalid answers / verification errors | 0 / 0 | 0 / 0 |

## By type (answerable questions)

| config | type | n | answer coverage | context coverage | false refusals | strict | lenient | citation precision |
|---|---|---|---|---|---|---|---|---|
| heading/hybrid | exact_term | 8 | 8 of 8 | 8 of 8 | 0 | 1.000 | 1.000 | 0.938 |
| heading/hybrid | mixed | 8 | 8 of 8 | 8 of 8 | 0 | 0.963 | 1.000 | 0.964 |
| heading/hybrid | conceptual | 10 | 5 of 10 | 5 of 10 | 5 | 0.909 | 1.000 | 0.833 |
| heading/dense | exact_term | 8 | 8 of 8 | 8 of 8 | 0 | 1.000 | 1.000 | 1.000 |
| heading/dense | mixed | 8 | 7 of 8 | 7 of 8 | 1 | 0.955 | 1.000 | 0.955 |
| heading/dense | conceptual | 10 | 8 of 10 | 7 of 10 | 2 | 0.933 | 1.000 | 0.903 |

## Paired comparison, hybrid vs dense (per question)

Outcomes (all 30 / the 26 answerable):

| both answered | only hybrid answered | only dense answered | both refused | other |
|---|---|---|---|---|
| 20 / 20 | 1 / 1 | 3 / 3 | 6 / 2 | 0 / 0 |

Where both configs answered and were verified (n = 20), comparing the per-question strict sentence share: hybrid higher in 2, equal in 16, lower in 2.

| id | type | hybrid | dense | hybrid strict share | dense strict share |
|---|---|---|---|---|---|
| e001 | exact_term | answered | answered | 1.00 | 1.00 |
| e002 | exact_term | answered | answered | 1.00 | 1.00 |
| e003 | exact_term | answered | answered | 1.00 | 1.00 |
| e004 | exact_term | answered | answered | 1.00 | 1.00 |
| e005 | exact_term | answered | answered | 1.00 | 1.00 |
| e006 | exact_term | answered | answered | 1.00 | 1.00 |
| e007 | exact_term | answered | answered | 1.00 | 1.00 |
| e008 | exact_term | answered | answered | 1.00 | 1.00 |
| m001 | mixed | answered | answered | 1.00 | 1.00 |
| m002 | mixed | answered | answered | 1.00 | 1.00 |
| m003 | mixed | answered | answered | 1.00 | 1.00 |
| m004 | mixed | answered | answered | 1.00 | 1.00 |
| m005 | mixed | answered | answered | 1.00 | 0.75 |
| m006 | mixed | answered | answered | 1.00 | 1.00 |
| m007 | mixed | answered | answered | 1.00 | 1.00 |
| m008 | mixed | answered | refused | 0.75 | - |
| c001 | conceptual | refused | answered | - | 1.00 |
| c002 | conceptual | refused | answered | - | 0.67 |
| c003 | conceptual | answered | answered | 0.86 | 1.00 |
| c004 | conceptual | answered | answered | 0.86 | 1.00 |
| c005 | conceptual | refused | answered | - | 1.00 |
| c006 | conceptual | answered | answered | 1.00 | 1.00 |
| c007 | conceptual | answered | answered | 1.00 | 0.67 |
| c008 | conceptual | answered | answered | 1.00 | 1.00 |
| c009 | conceptual | refused | refused | - | - |
| c010 | conceptual | refused | refused | - | - |
| u001 | unanswerable | refused | refused | - | - |
| u002 | unanswerable | refused | refused | - | - |
| u003 | unanswerable | refused | refused | - | - |
| u004 | unanswerable | refused | refused | - | - |
