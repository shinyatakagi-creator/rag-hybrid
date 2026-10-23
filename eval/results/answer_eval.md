# Answer eval

Git `6220fb4` | 2026-10-23T05:22:10+00:00 | answers `claude-sonnet-5-5` (effort medium), verifier `claude-haiku-5-5` (claims-v2, effort low) | cost from logs $0.7289

Faithfulness strict = sentences with at least one cited excerpt judged yes; lenient = yes or partial. Citation precision = share of cited pairs judged yes. The verifier's own accuracy is not established until the checkpoint-4 hand labels.

| config | answered / refused / invalid | correct refusals (of 4) | answered unanswerable | false refusals (of 26) | faithfulness strict | lenient | citation precision | sentences |
|---|---|---|---|---|---|---|---|---|
| heading/hybrid | 21 / 9 / 0 | 4 | 0 | 5 | 0.959 | 1.000 | 0.910 | 73 |
| heading/dense | 23 / 7 / 0 | 4 | 0 | 3 | 0.961 | 1.000 | 0.951 | 77 |

Answerable questions only:

| config | questions | strict | lenient | citation precision | context holds an expected doc |
|---|---|---|---|---|---|
| heading/hybrid | 20 | 0.959 | 1.000 | 0.910 | 21 of 26 |
| heading/dense | 23 | 0.961 | 1.000 | 0.951 | 22 of 26 |

By type:

| config | type | n | false refusals | strict | lenient |
|---|---|---|---|---|---|
| heading/hybrid | exact_term | 8 | 0 | 1.0 | 1.0 |
| heading/hybrid | mixed | 8 | 0 | 0.963 | 1.0 |
| heading/hybrid | conceptual | 10 | 5 | 0.909 | 1.0 |
| heading/dense | exact_term | 8 | 0 | 1.0 | 1.0 |
| heading/dense | mixed | 8 | 1 | 0.955 | 1.0 |
| heading/dense | conceptual | 10 | 2 | 0.933 | 1.0 |
