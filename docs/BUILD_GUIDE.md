# RAG Pipeline with Hybrid Search Over Internal Docs: Build Guide

## Handover: read this first (instructions for Claude Code)

This file is the spec. Build the repo described below in a new directory `rag-hybrid/`.

**Division of work:** Claude Code builds the whole repo end to end, including retrieval, generation, verification and eval scripts. (If the owner wants to write the core modules himself, he will change this line to "scaffold only; he writes `rag/retrieve.py`, `rag/verify.py` and `eval/*`, you review".)

**How to work**
- One phase at a time, in order. At the end of each phase, run the acceptance check below, show the output, and wait for a go-ahead before starting the next phase.
- Never commit `.env` or any key. Commit `.env.example`. Add `.env`, `data/`, and the embedding cache to `.gitignore`.
- Before any paid API call (embeddings, answer generation, verification, question drafting), print the estimated token count and cost and wait for confirmation. Enforce `MAX_SPEND_USD` in code: abort the run when the running total would exceed it.
- Look up current model IDs (Claude Sonnet for answers, a Haiku-class model for verification, OpenAI `text-embedding-3-small`) and the current ES 9.x image tag. Pin them in `.env.example` and `docker-compose.yml`. Do not guess IDs from memory.
- Do not invent eval numbers. Every number in the README comes from a run whose output is saved under `eval/results/`.
- If something in this guide conflicts with what the installed library or the running ES actually does (for example, a changed default), follow reality, note the difference in `NOTES.md`, and carry on.

**Human checkpoints (stop and ask; do not skip or fake these)**
1. Corpus pinned: show the commit SHA and the page count before chunking.
2. Golden set: Claude Code may draft candidate questions, but the owner reviews them and chooses the final expected `doc_id`s. Stop after drafting.
3. Native RRF cross-check: the owner starts the 30-day trial licence (`POST _license/start_trial?acknowledge=true`). Do not attempt it yourself.
4. Verifier spot-check: print 25 sampled verifier judgements (sentence, chunk, verdict) for the owner to label by hand, then compute agreement from his labels.
5. README results and CV bullet: fill in only after the owner has seen the saved eval outputs.

**Configuration (`.env.example`)**
```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
EMBED_MODEL=text-embedding-3-small
ANSWER_MODEL=        # current Claude Sonnet ID
VERIFIER_MODEL=      # current Haiku-class ID
ES_URL=http://127.0.0.1:9200
ES_INDEX=rag-docs
FUSION=python        # python | native
MAX_SPEND_USD=5
```

**Commands (keep these names stable)**
```
python -m ingest.run --corpus-dir data/k8s --chunker both   # load + chunk, writes data/chunks/*.jsonl
python -m ingest.index                                      # embed (cached) + bulk index
python -m eval.draft_questions                              # drafts candidates, then stops for human review
python -m eval.retrieval_eval --fusion python               # also: --fusion native
python -m eval.answer_eval
uvicorn api.main:app --port 8000
pytest
```

**Golden set format (`eval/golden.jsonl`, one JSON object per line)**
```
{"id": "q001", "type": "exact_term | conceptual | mixed | unanswerable", "question": "...", "expected_doc_ids": ["..."], "reference_answer": "...", "answerable": true}
```
`doc_id` is the page path relative to the corpus root, without extension. Make `chunk_id` a stable hash of `doc_id + chunker + chunk position + content`, so cached vectors survive re-chunking only when the content is unchanged.

**Acceptance checks per phase**

| Phase | Done when |
|---|---|
| 0 Setup | `docker compose up -d` gives a healthy single-node ES with the 1 GB heap; `pytest` runs (even if empty); `.env.example` present |
| 1 Chunking | Both chunkers produce jsonl; stats printed (chunks per chunker, token count min/median/max); no chunk over 800 tokens; chunker unit tests pass |
| 2 Index | Doc counts per chunker match the chunk files; `GET rag-docs/_mapping` output saved to `eval/results/mapping.json` with the effective `index_options`; re-running the indexer makes zero new embedding calls |
| 3 Retrieval | `/search` style function works for bm25, dense and hybrid on both chunkers; one hand-picked query per mode returns sensible hits |
| 4 Python RRF | Unit tests pass (doc in one list only, ties, empty list, hand-computed scores) |
| 5 Generation | `/ask` returns structured `{sentence, citations}`; an out-of-corpus question gets a refusal, not an answer |
| 6 Verification | Verdicts returned per sentence; citation precision and unsupported-sentence list computed; owner spot-check done (checkpoint 4) |
| 7 Eval | Results tables written to `eval/results/` for all six chunker/mode rows, split by question type; native vs Python top-k overlap reported |
| 8 API + Docker | From a fresh clone: `docker compose up`, run ingest and index, then hit `/search` and `/ask` successfully |

---

Source: slide "Project 6" (repo/README name it Project 08 so it doesn't clash with support-agent, which is Project 06, and voice agent, which is 07). No overlap with Projects 01-05.

Overlap note: your support-agent has a KB search tool. Build this as a standalone retrieval service, then have support-agent call it later as a follow-up commit. That turns two projects into one coherent story instead of two separate KB searches.

A RAG system that ingests a docs corpus, indexes it for both keyword (BM25) and dense vector search, fuses the results, generates answers with inline citations, and verifies each citation actually supports the sentence it's attached to.

Target: finishable on a local laptop in about a week of evenings, public GitHub repo, and a CV bullet backed by your own eval numbers.

## Key adaptation: use Elasticsearch for both retrievers

The slide splits sparse and dense across rank_bm25 and a vector DB. Elasticsearch does BM25 and kNN in one index. You know the engine inside out, so this is where you can show depth the average candidate can't: mappings, analyzers, `num_candidates` tuning, and why RRF beats score normalisation. Keep a short section in the README explaining why you didn't use Chroma + rank_bm25.

## Licence gotcha: the native RRF retriever needs Enterprise

The `rrf` retriever (and the `linear` retriever) is Enterprise-gated. On a fresh local cluster (Basic licence) it returns a 403 `security_exception: current license is non-compliant for [Reciprocal Rank Fusion (RRF)]`. This has been true since the 8.8 preview through 9.x.

So the plan is:
1. **Default path: your own Python RRF** (Phase 4). Runs on any licence, so anyone cloning the repo can run it.
2. **Cross-check: native `rrf` retriever** on a 30-day trial (`POST _license/start_trial?acknowledge=true`, once per major version). Run both on the golden set and confirm the rankings match. Explaining why your fusion matches Elasticsearch's, and why the licence gating matters for a portable repo, is a strong README section and interview answer.
3. Make fusion switchable in config (`FUSION=python|native`) and default to `python`.

## Ground rules

- Public docs you're allowed to index. Corpus: Kubernetes docs (`kubernetes/website`, CC BY 4.0, all markdown). Lots of exact terms (flags, field names, error strings) for the BM25-wins questions and lots of conceptual pages for the dense-wins ones. Avoid Elastic's own docs; indexing your employer's content in a job-search project looks odd.
- Pin the corpus: clone `kubernetes/website` at a fixed commit, record the SHA in `data/CORPUS.md`, and index only `content/en/docs/concepts`, `content/en/docs/tasks` and `content/en/docs/reference` (skip generated API reference pages if the count goes over about 500 pages). The golden set depends on this staying fixed. Add attribution (CC BY 4.0, source repo and SHA) to the README.
- Secrets in `.env`, with a `.env.example` committed. Spend limit set on the API keys.
- Pin dependency versions and the ES image tag.

## Stack (adapted)

| Component | Slide | Use | Why |
|---|---|---|---|
| Language | Python 3.11+ | Same | |
| Embeddings | OpenAI text-embedding-3-small | Same | Cheap, 1536 dims, matches the mapping below |
| Vector store | ChromaDB or Qdrant | Elasticsearch `dense_vector` | One engine for both retrievers, and it's your strongest stack |
| Sparse search | BM25 via rank_bm25 | Elasticsearch BM25 | Real analyzers and field boosts instead of an in-memory index |
| LLM (answers) | GPT-4o or Claude Sonnet | Claude Sonnet (model ID in `.env`) | Grounding and citation |
| LLM (verifier) | n/a | Haiku-class model (model ID in `.env`) | Cheap yes/partial/no judgements |
| Chunking | LangChain text splitters | Same | `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter` |
| API | FastAPI | Same | |
| Containerization | Docker | Docker Compose (ES + API, Kibana behind a profile) | Light enough for a laptop |

Offline option: swap OpenAI embeddings for a local model such as bge-small via sentence-transformers. Dims become 384, so change the mapping to match. Only do this if you want a "no external API" angle; the default story is OpenAI embeddings.

## Laptop budget

**Resources**
- ES single node, heap capped: `ES_JAVA_OPTS=-Xms1g -Xmx1g`. Give Docker Desktop about 4 GB.
- Kibana is optional: put it behind a compose profile (`--profile debug`) and use it for screenshots and debugging only.
- Corpus: 300-500 markdown pages, roughly 5,000-8,000 chunks per chunker. At 1536 dims that's well under 200 MB of vectors for both chunkers.
- Embed once and cache vectors on disk (jsonl or parquet keyed by chunk hash + model name). Re-indexing after a mapping change then costs nothing and takes seconds.

**Cost (set a hard spend limit regardless)**
- Embedding about 5M tokens with text-embedding-3-small: around 10 cents.
- Retrieval evals (recall@k, MRR) use no LLM, so rerun them freely.
- Only run answer generation for hybrid + heading chunker, plus BM25 as a baseline: about 55 questions through Sonnet, verification on a Haiku-class model. Expect a few dollars total.
- Record cost per answered question in the API response and the README.

## Scope for a finishable version

Must-haves:
1. Markdown only (skip the HTML loader).
2. Both chunkers, fixed and heading-aware. The comparison is half the findings.
3. Three modes: BM25, dense, hybrid via your Python RRF, with the native retriever as a trial-licence cross-check.
4. Generation with numbered citations, plus citation verification.
5. The 50-question golden set and the results table.
6. FastAPI `/search` and `/ask`, Docker Compose.
7. A few tests: the RRF function, the chunker, and one API smoke test.

Defer to follow-up commits: Chroma/Qdrant comparison, cross-encoder reranker, query rewriting, HTML loader, support-agent hookup.

## What "done" looks like

- Ingestion for markdown docs with heading-aware chunking (HTML optional)
- One Elasticsearch index with text fields and a `dense_vector` field, `index_options` recorded in the README
- Three retrieval modes: BM25, dense, hybrid (RRF), switchable per request
- Hybrid fusion implemented in Python, cross-checked against the native `rrf` retriever
- Answer generation with numbered citations `[1]` linked to chunk URLs
- Citation verification that flags unsupported sentences
- A 50-question golden set and a table comparing the three modes on recall@k and MRR, plus answer faithfulness
- FastAPI `POST /ask` and `POST /search`, Docker Compose for ES + API
- Clean-clone check: `docker compose up` plus one ingest command works from scratch

## Repo layout

```
rag-hybrid/
├── ingest/
│   ├── loaders.py        # markdown (html optional) → sections with heading path
│   ├── chunkers.py       # fixed-size vs heading-aware
│   ├── embed_cache.py    # on-disk vector cache keyed by chunk hash + model
│   └── index.py          # bulk index from cache
├── rag/
│   ├── retrieve.py       # bm25 / dense / hybrid (python rrf, native rrf)
│   ├── generate.py       # prompt with numbered chunks
│   └── verify.py         # citation support check
├── api/main.py
├── eval/
│   ├── draft_questions.py # model-drafted candidates from sampled chunks
│   ├── golden.jsonl       # question, type, expected doc_ids, reference answer
│   ├── retrieval_eval.py
│   └── answer_eval.py
├── tests/
├── docker-compose.yml    # ES (heap capped), API; Kibana under a profile
├── .env.example
└── pyproject.toml
```

## Phase 0: setup

Single-node ES 9.x, security off, ports bound to 127.0.0.1, heap capped. Reuse the compose file from support-agent if it exists and add the heap setting and Kibana profile.

```bash
uv venv && source .venv/bin/activate
uv pip install elasticsearch openai anthropic fastapi uvicorn python-dotenv beautifulsoup4 tiktoken langchain-text-splitters pytest
```

Pin the versions in `pyproject.toml` once it works.

## Phase 1: loading and chunking (Day 1-2)

Load each doc into sections keyed by heading path (`Install > macOS > Homebrew`). Then build two chunkers so you can measure the difference:

- Fixed: `RecursiveCharacterTextSplitter.from_tiktoken_encoder(chunk_size=400, chunk_overlap=50)`, ignores structure
- Heading-aware: `MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")])` first, then the recursive splitter (~600 tokens) on any section that's still too long. Merge tiny sections into the next one, and prefix each chunk with its heading path from the splitter's metadata

Each chunk record: `chunk_id, doc_id, url, title, heading_path, content, token_count, chunker`.

Strip Hugo shortcodes and front matter from the Kubernetes docs before chunking, and map each file path to its public URL for citations.

## Phase 2: index (Day 2)

```json
PUT rag-docs
{
  "mappings": {
    "properties": {
      "doc_id":       { "type": "keyword" },
      "chunker":      { "type": "keyword" },
      "url":          { "type": "keyword" },
      "title":        { "type": "text" },
      "heading_path": { "type": "text" },
      "content":      { "type": "text", "analyzer": "english" },
      "embedding":    { "type": "dense_vector", "dims": 1536, "similarity": "cosine", "index": true }
    }
  }
}
```

Embed `heading_path + "\n" + content` in batches of 100 and write the vectors to the cache before indexing, then bulk index from the cache with `helpers.bulk`. Index both chunker variants into the same index, filtered by the `chunker` field at query time, so the eval can compare them without re-indexing.

After creating the index, run `GET rag-docs/_mapping` and record the effective `index_options` (recent 9.x releases may quantise `dense_vector` by default). If dense recall is lower than expected, check this first; comparing the default against an explicit `hnsw` / `int8_hnsw` / `bbq_hnsw` setting is a good tuning result for the README.

## Phase 3: retrieval modes (Day 3)

BM25-only and dense-only are the two inner queries run on their own. Hybrid fuses them (Phase 4 default, native below as a cross-check).

Native retriever (needs trial or Enterprise licence):

```python
def hybrid_native(es, q, vec, chunker="heading", k=8):
    return es.search(index="rag-docs", size=k, retriever={
        "rrf": {
            "retrievers": [
                {"standard": {"query": {"bool": {
                    "must": {"multi_match": {"query": q, "fields": ["title^2", "heading_path^1.5", "content"]}},
                    "filter": {"term": {"chunker": chunker}}}}}},
                {"knn": {"field": "embedding", "query_vector": vec, "k": 50,
                         "num_candidates": 200, "filter": {"term": {"chunker": chunker}}}},
            ],
            "rank_window_size": 50,
            "rank_constant": 60,
        }
    })
```

## Phase 4: Python RRF (default path)

Run the BM25 and kNN queries separately (each with `size=50`, same `chunker` filter), then fuse:

```python
def rrf(result_lists, k=60, top_n=8):
    scores = {}
    for results in result_lists:
        for rank, hit in enumerate(results, start=1):
            scores[hit["_id"]] = scores.get(hit["_id"], 0) + 1 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)[:top_n]
```

Unit test it with hand-computed examples (a doc ranked 1st in one list and absent from the other, ties, empty lists). Then run native vs Python on the golden set and report the overlap in top-k.

## Phase 5: generation with citations (Day 4)

Pass chunks numbered `[1]..[n]` with their heading path. Instructions: every factual sentence ends with one or more citations; if the chunks don't contain the answer, say so and stop. Return structured output: a list of `{sentence, citations: [int]}` so verification is easy.

## Phase 6: citation verification (Day 4-5)

For each sentence, ask a small, cheap model: "Does chunk [n] support this sentence? yes / partial / no." Batch all sentences in one call to keep cost down. Report:
- Citation precision: share of citations judged "yes"
- Unsupported sentences: shown to the user with a warning marker

Optional cheaper first pass: token overlap between sentence and chunk; only send low-overlap pairs to the LLM.

Spot-check 20-30 verifier judgements by hand and report the agreement rate. A verifier you haven't checked is a weak claim.

## Phase 7: evaluation (Day 5-6)

Golden set: 50 questions, each with 1-3 expected `doc_id`s and a short reference answer. Include about 10 exact-term questions (config names, error strings, flags, version numbers), where BM25 should win, 10 paraphrased conceptual ones, where dense should win, 5 questions whose answers aren't in the corpus, and the rest mixed.

Writing 50 by hand is the slowest part. Faster: `draft_questions.py` has a model draft candidate questions from sampled chunks (including each category above), then you review, fix, and cut them, and pick the expected doc_ids yourself. State this in the README; it's normal practice and honest.

`retrieval_eval.py` output, the table that goes in the README (no LLM calls, rerun freely):

| Chunker | Mode | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|
| fixed | bm25 | | | |
| fixed | dense | | | |
| fixed | hybrid | | | |
| heading | bm25 | | | |
| heading | dense | | | |
| heading | hybrid | | | |

Also report the table split by question type (exact-term vs conceptual) so the hybrid result is visible per slice.

`answer_eval.py` (hybrid + heading, BM25 as baseline): faithfulness (share of sentences verified as supported), citation precision, and "answered when it should have refused" on the 5 out-of-corpus questions. Log cost and latency per question.

## Phase 8: API and Docker

`POST /search {query, mode, chunker, k}` returns chunks with scores. `POST /ask {query}` returns answer, citations, verification results, latency and cost. Add the API to the compose file. Final check: clone the repo into a fresh directory, `docker compose up`, run the ingest command, and hit both endpoints.

## Demo and write-up

- Demo: an exact error-string question where dense misses and hybrid gets it, then a paraphrased question where BM25 misses and hybrid gets it (record a short GIF or video for the README)
- README: results table, chunking findings, why ES over Chroma + rank_bm25, the RRF licence note and native-vs-Python cross-check, `index_options` finding, cost per question, known limits

## CV bullet (fill in from your own eval only)

> Built a hybrid-search RAG service on Elasticsearch (BM25 + kNN with reciprocal rank fusion) over [corpus], with heading-aware chunking and citation verification. On a 50-question golden set, hybrid reached [X] recall@5 and [Y] MRR versus [A]/[B] for BM25 and [C]/[D] for dense; verification flagged [Z]% of unsupported sentences. Cost [N] cents per answered question.

If hybrid doesn't win on some slice, report it anyway and say what you changed. "Dense lost on exact terms, here's why" reads better than a clean sweep.

## Stretch (after the core is done)

- Hook into support-agent as its `search_kb` tool and rerun that project's evals
- The slide's stack (Chroma or Qdrant + rank_bm25) on the same chunks and golden set, compared against ES hybrid
- Reranker on the top 50 (a cross-encoder) and its effect on MRR
- Query rewriting for multi-part questions
- HTML loader
