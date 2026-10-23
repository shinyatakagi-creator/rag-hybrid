# Correctness check

Judge `claude-haiku-5-5` (effort low); cost $0.0073. Pre-registered; the judge sees the question, the reference answer and the answer text only. It measures agreement with the reference answers, which were written from the expected pages; it is not an independent truth check, and the judge itself is unvalidated.

| config | answers judged | covered yes | partial | no | contradicts reference | clean (yes and no contradiction) | errors |
|---|---|---|---|---|---|---|---|
| heading/hybrid | 21 | 18 | 3 | 0 | 2 | 18 | 0 |
| heading/dense | 23 | 18 | 5 | 0 | 2 | 18 | 0 |

## Judge controls (pre-registered: 3 swapped to an unrelated question, 3 with an inverted claim or changed number, 2 faithful rewordings; built from heading/dense answers)

Wrong controls caught (key facts `no` or contradicts `yes`): **6 of 6**. Correct controls wrongly failed (not clean): **0 of 2**. Control errors (invalid judge output): 0. Controls are excluded from the table above.

| control | kind | built from | expected | covered | contradicts | caught / clean | reason |
|---|---|---|---|---|---|---|---|
| S1 | swapped | e002 | wrong | no | no | caught / not clean | Answer describes the kube-apiserver --service-account-max-token-expiration flag, which is unrelated to freeing node capacity for DaemonSet pods; it does not address the question at all. |
| S2 | swapped | m001 | wrong | no | no | caught / not clean | Answer discusses --root-ca-file and ServiceAccount CA bundles, not --runtime-config for disabling API groups; it answers a different question. |
| S3 | swapped | e005 | wrong | no | no | caught / not clean | The answer discusses scheduler preBind plugins and never addresses the acquireTime field or when leadership was acquired. |
| A1 | inverted claim | m002 | wrong | no | yes | caught / not clean | The answer claims setting the flag to false enables Priority and Fairness, directly opposite to the reference stating it disables the feature. |
| A2 | changed number | m003 | wrong | partial | yes | caught / not clean | Answer names both required options but attributes them to Cosign 1.0, while the reference says Cosign 2.0. |
| A3 | inverted claim | m006 | wrong | no | yes | caught / not clean | Answer says kubelet accepts the pod and ignores the option, while reference says kubelet rejects Pods using bindMountOptions when runtime lacks support. |
| R1 | faithful rewording | e004 | correct | yes | no | missed / clean | Answer states acquireTime records the time leadership was obtained, matching the reference's timestamp of leadership acquisition. |
| R2 | faithful rewording | e008 | correct | yes | no | missed / clean | Answer states tokens bound to MutatingWebhookConfiguration get the uid key in .status.user.extra after TokenReview verification, matching the reference; it omits the name key and validating counterpart but that is not required here. |
