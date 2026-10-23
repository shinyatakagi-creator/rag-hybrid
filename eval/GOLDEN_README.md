# Golden set: fields, doc_ids, helpers

The final set is `eval/golden.jsonl` (one JSON object per line, 50 questions). You write the 10 `exact_term` and 5
`unanswerable` questions into **`eval/golden_owner.jsonl`**; `python -m eval.draft_questions` drafts the `conceptual`
(about 20) and `mixed` (about 15) candidates into `eval/golden_drafts.jsonl`, and you choose the final
`expected_doc_ids`. `eval/golden_template.jsonl` shows one example line per type (its REPLACE placeholders make it fail
the checker on purpose).

## Fields

| field | meaning |
|---|---|
| `id` | any unique string (`e01`, `u03`, ...). I renumber to `q001`..`q050` when merging the final file |
| `type` | `exact_term` \| `conceptual` \| `mixed` \| `unanswerable` |
| `question` | what a user would type |
| `expected_doc_ids` | 1-3 `doc_id`s of the pages that answer it; `[]` for `unanswerable` |
| `reference_answer` | one or two sentences, from the pages; `""` is fine for `unanswerable` |
| `answerable` | `true`, except `false` for `unanswerable` |
| `note` | optional free text. 1-3 expected docs is the plan; more than 3 gives a *warning* (not an error), and a non-empty `note` saying why silences it. At least 1 expected doc is still required for answerable questions |

**Types.** `exact_term`: the question contains an exact flag, field name, command or error string that appears in the
docs (BM25 should do well). `conceptual`: everyday words, avoiding the page's own vocabulary (dense should do well).
`mixed`: one exact term plus a conceptual aspect. `unanswerable`: a Kubernetes question the 502 pages do not answer;
the interesting ones sit next to the corpus (for example a kubelet flag default, which lives only in the excluded
`reference/command-line-tools-reference`), because an off-topic question is an easy refusal.

## doc_ids

- **The list of all indexed pages: `eval/doc_ids.tsv`** (502 rows: `doc_id`, `url`, `title`, `chunks_fixed`,
  `chunks_heading`). Open it in an editor or spreadsheet. Regenerate with `python -m eval.docids --write`.
- A `doc_id` is the page path under `content/en/docs/` without `.md`, e.g. `concepts/policy/pid-limiting`. A section
  page keeps `_index`: `concepts/workloads/pods/_index` (its URL is the directory).
- **URL to doc_id:** drop `https://kubernetes.io/docs/` and the trailing slash. For a section URL add `/_index`.
  Not sure which? `python -m eval.docids --url https://kubernetes.io/docs/concepts/workloads/pods/` tries both and
  tells you if the page is not indexed. Other lookups: `--title "id limits"` (a substring of the page *title*, here
"Process ID Limits And Reservations"; it does not search doc_ids or text), `--id concepts/policy/pid-limiting`.
- **25 listed pages have 0 chunks** (bare section indexes with no body text). They cannot be retrieved, so the checker
  rejects them as expected ids. Pages in the excluded folders (`kubernetes-api`, `glossary`,
  `command-line-tools-reference`, `setup-tools`, `kubectl`) and the headless partials are not in the list at all.

## Helpers

```bash
# how many chunks / docs contain a term, per chunker (flag-like terms: use --term=... or put them after --)
python -m eval.term_stats --term=--max-requests-inflight --term=maxUnavailable --show 10
python -m eval.term_stats -- --max-requests-inflight

# validate your file: format, known doc_ids with chunks, at least 1 expected doc (warning above 3), counts against the 10/20/15/5 plan
python -m eval.golden_check eval/golden_owner.jsonl
```

`term_stats` is a literal, case-insensitive substring match on the cleaned chunk text (use `--case` for exact case).
For an `exact_term` question you want the term in only a handful of pages and `expected_doc_ids` to list them.

## Keeping the set honest

- **Choose `expected_doc_ids` from your own reading of the docs, not from what the search system returns.** Picking
  them from retrieval output would favour whichever retriever produced it. Nothing in the drafts shows retrieval results.
- A drafting model sees one passage, so it cannot know that a second page also answers the question. List every page
  that genuinely answers it (up to 3); otherwise recall is understated.
- Do not run retrieval or answer evals until the final set is fixed.
