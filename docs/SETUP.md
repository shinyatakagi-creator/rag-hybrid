# Setup: from a fresh clone to a running system

Follow these steps in order. Commands are run from the repository root unless stated. Everything that costs money is marked **PAID** and
prints an estimate first; nothing in this guide calls a paid API without it.

| step | what | cost |
|---|---|---|
| 7 | embed the corpus (once) | about $0.05 (`text-embedding-3-small`, about 2.7 M tokens) |
| 9 | optional retrieval evaluation | about $0.00001 (26 query embeddings) |
| API `/search` (dense or hybrid) | one query embedding | about $0.0000002 |
| API `/ask` | one answer (Claude Sonnet) plus one verification (Claude Haiku) | about $0.013 typical, $0.05 at most |

## 1. Prerequisites
- Docker with Compose v2 (tested with Docker 29.8 and Compose 5.5), about 6 GB free disk and about 3 GB of RAM available to Docker for Elasticsearch (1 GB heap).
- Python 3.12 and git.
- An OpenAI API key (embeddings) and an Anthropic API key (answers and verification). Set a spend limit on both accounts as well.
- Internet access (GitHub for the corpus, PyPI, the two providers).

## 2. Clone and configure
```bash
git clone <this repository's URL> rag-hybrid
cd rag-hybrid
cp .env.example .env
```
Edit `.env`: fill in `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`. The other values are pinned defaults (`EMBED_MODEL`, `ANSWER_MODEL`, `VERIFIER_MODEL`, `ES_URL`,
`ES_INDEX=rag-docs`, `MAX_SPEND_USD=5`). `.env` is git-ignored; never commit it. Keep `ES_URL` as it is: the host scripts use `127.0.0.1:9200`
(the API container overrides it to the compose network itself).

If you already run another Elasticsearch on port 9200, or an earlier copy of this project, read section 11 first.

## 3. Python environment (for ingestion, evaluation, tests)
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
`requirements.txt` pins every package that was used to produce the committed results.

## 4. Corpus
```bash
scripts/fetch_corpus.sh
```
Clones `kubernetes/website` at the pinned commit (`6c42e266fcc1f0e0edd4805baea904e1b3cbaf9c`, shallow, sparse: `content/en/docs/{concepts,tasks,reference}`, `content/en/examples`,
`content/en/includes`) into `data/k8s-src` and links `data/k8s`. It **fails** if the commit is not the pinned one or if the corpus does not load as
502 pages with 477 of them producing chunks. The pin and the scope are described in `docs/CORPUS.md`. Do not update the checkout: the golden set depends on it.

## 5. Elasticsearch
```bash
docker compose up -d es
docker compose ps        # wait until es shows (healthy), usually under a minute
```
This starts a single-node Elasticsearch 9.5.5 (security off, 1 GB heap) published on `127.0.0.1:9200` only, with its data in the Docker volume `esdata`.

## 6. Chunk the corpus (free)
```bash
python -m ingest.run --corpus-dir data/k8s --chunker both
```
Writes `data/chunks/fixed.jsonl` (4,072 chunks) and `data/chunks/heading.jsonl` (4,527 chunks) and `eval/results/chunk_stats.json`. The run must report `pages=502`
and no chunk over 800 tokens. The output files are identical, byte for byte, on every machine we have checked.

## 7. Embed and index (**PAID**, once)
```bash
python -m ingest.index --dry-run     # prints unique texts, tokens, estimated cost; no API call
python -m ingest.index               # asks for confirmation, then embeds and bulk-indexes (add --yes to skip the prompt, e.g. in a script)
```
With no embedding cache present the dry run reports 8,577 unique texts, 2,670,798 tokens, about $0.053. `MAX_SPEND_USD` aborts the run if the estimate exceeds it.
Vectors are cached in `data/embed_cache/text-embedding-3-small.jsonl` (git-ignored, about 0.3 GB), so a re-run costs nothing. The index is named by `ES_INDEX`.

## 8. Check the index
```bash
curl -s "127.0.0.1:9200/_cat/indices?v"                                  # rag-docs, 8599 docs
curl -s "127.0.0.1:9200/rag-docs/_count?pretty" -H 'content-type: application/json' -d '{"query":{"term":{"chunker":"heading"}}}'   # 4527
```
`eval/results/mapping.json` (written by the indexer) records the effective `dense_vector` `index_options`.

## 9. Optional: reproduce the retrieval baseline
```bash
python -m eval.retrieval_eval --dry-run     # query-embedding estimate (about $0.00001), no API call
python -m eval.retrieval_eval --yes --out-json eval/results/retrieval_repro.json --out-md eval/results/retrieval_repro.md   # the 6 rows on the 26 answerable golden questions
```
The output goes to separate `retrieval_repro.*` files so the committed baseline is not overwritten. Compare `eval/results/retrieval_repro.json` with the committed `eval/results/retrieval_baseline.json`. BM25 rows should match exactly; dense and hybrid rows can differ slightly, because embeddings produced by a new API call are not bit-identical
to the ones in the original cache, and Elasticsearch approximate nearest-neighbour search is not guaranteed to be deterministic across indexes.

## 10. Run the API
**Supported mode: Docker Compose.**
```bash
docker compose up -d          # builds the API image the first time; es must be healthy (the api service waits for it)
docker compose ps             # both healthy; the API is published on 127.0.0.1:8000 only
curl -s -X POST http://127.0.0.1:8000/search -H 'content-type: application/json' -d '{"query":"kubectl drain","mode":"bm25","k":3}'    # free
```
- The spend ledger, request logs and the serving query-embedding cache live in the Docker volume `apidata` (`/app/data` in the container), so `MAX_SPEND_USD` survives container recreation.
  The ledger starts at $0; the API counts only what it spends itself. If you have already spent money elsewhere (for example the section 7 embedding, about $0.05) and want it counted against the
  same limit: `docker compose exec api python -m api.ledger seed 0.06`. Check it with `docker compose exec api python -m api.ledger status`.
- `/search` with `mode` `dense` or `hybrid` embeds the query (about $0.0000002); `/ask` answers and verifies (about $0.013). Both are refused with HTTP 429 and no paid call once the limit would be exceeded.
- Running the API directly on the host (`python -m api.main`) also works and uses its own ledger in `data/api/`; do not use both for real spend, their ledgers are separate.
- Stop with `docker compose down` (keeps both volumes). `docker compose down -v` deletes the Elasticsearch index and the ledger.

## 11. If you already run this stack, or another Elasticsearch
- **The Compose project name is fixed** (`name: rag-hybrid` at the top of `docker-compose.yml`), so it does not depend on the folder you cloned into. Every clone, in any folder, shares the same
  containers and volumes: a second clone attaches to the Elasticsearch that is already running (`docker compose up -d es` reports it as `Running`) instead of starting a second one that fights for port 9200.
  If you want a completely separate stack instead, use `docker compose -p other-name ...` **and** give it other host ports (below).
- **Something else already uses port 9200 (or 8000):** set `ES_HOST_PORT` / `API_HOST_PORT` in `.env` (see `.env.example`) and change the port in `ES_URL` to match, then run `docker compose up -d`.
- **To leave an existing index alone**, set a different `ES_INDEX` in `.env` (for example `rag-docs-check`) before steps 7 to 10, and delete it when you are done:
  `curl -X DELETE 127.0.0.1:9200/rag-docs-check`. The API container reads `ES_INDEX` from the same `.env`.

## 12. Tests
```bash
pytest -q       # about 30 s; needs Elasticsearch up (a few tests use a throwaway test index); makes no paid call
```

## 13. Corpus attribution
The indexed text is derived from the Kubernetes documentation, repository <https://github.com/kubernetes/website> at commit `6c42e266fcc1f0e0edd4805baea904e1b3cbaf9c`,
copyright The Kubernetes Authors, licensed under **Creative Commons Attribution 4.0 International (CC BY 4.0)**, <https://creativecommons.org/licenses/by/4.0/>.
The project uses a subset of the pages, cleaned of Hugo shortcodes and chunked; the chunks are modified material. No endorsement by The Kubernetes Authors is implied.
The corpus is downloaded by `scripts/fetch_corpus.sh` and is not stored in this repository or in the Docker image.
