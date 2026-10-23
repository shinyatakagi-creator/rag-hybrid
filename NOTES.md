# NOTES: deviations from the build guide and things that differ from what it assumes

## Phase 0
- Directory: built in `rag-hybrid/` inside the working dir `rag-hybrid-search-build-guide/`.
- ES 9 has security on by default; compose sets `xpack.security.enabled=false` (guide: "security off").
- `pytest` with no tests exits 5 ("no tests collected"); Phase 1 adds real tests.
- Python pinned to 3.12 (system python is 3.15). Exact dependency pins in `pyproject.toml`.
- `FUSION` env var removed from `.env.example` (accepted cut). Fusion becomes `--fusion python|native` on the eval CLI.

## Phase 1
- **Corpus scope B** (511 pages) instead of the guide's "about 500 pages incl. all reference": excluded `reference/{kubernetes-api,glossary,command-line-tools-reference,setup-tools,kubectl}`. See `data/CORPUS.md` (SHA `6c42e266...`).
- **`--corpus-dir data/k8s`** is a symlink to `data/k8s-src/content/en` so `docs/`, `examples/` and `includes/` are all reachable. Only `docs/{concepts,tasks,reference}` become documents; `examples/` and `includes/` are read only to resolve `code_sample` / `include`.
- **doc_id** = path under `docs/` without `.md`, so `_index` pages are `.../_index` (their URL is the directory). No `docs/` prefix.
- **Shortcodes**: `include` inlined (except boilerplate `task-tutorial-prereqs.md`, 121 uses, stripped so identical text does not skew BM25), `code_sample` inlined as fenced blocks (7 references use a leading `/`; handled), `glossary_tooltip` -> its text, `glossary_definition` -> inlined short/full definition from the (checked-out but not indexed) glossary pages, notes/cautions -> "Note:" etc., `skew`/`param`/`version-check`/`thirdparty-content` stripped (build-time computed values are lost). Unknown shortcodes (`api-reference`, `example`, `link`, `page-api-reference`, `cve-feed`, `pageinfo`, `legacy-repos-deprecation`) are stripped and counted in the run output.
- **Hugo closing tags** are sometimes `{{</ name >}}` (space after the slash); the cleaner accepts both.
- **Layout HTML** (`td`, `tr`, `span`, ...) is stripped outside code fences, text kept.
- **Heading prefix**: the guide says both "prefix each chunk with its heading path" (Phase 1) and "embed heading_path + newline + content" (Phase 2). `content` is stored without the prefix and the prefix is added only when embedding, so it is not duplicated. `token_count` and the 800-token limit are measured on the embedded text.
- **Fixed chunker** gets only the page title as `heading_path` (structure-blind by design); it still obeys 800 tokens. **Yes, its embedded text also gets a prefix**: `embed_text()` is `heading_path + "\n" + content` for both chunkers, so a fixed chunk is embedded as `<page title>\n<content>`. The heading chunker gets the full path (`Title > H2 > H3`). So the chunker comparison differs in chunk boundaries and heading depth, not in whether a prefix exists; the fixed baseline is not prefix-free. BM25 `title` / `heading_path` fields are likewise populated for both.
- **Tiny-section merge** (<100 tokens) only happens inside one parent heading: into a descendant (intro -> first H2, empty H2 -> first H3) or between H3 siblings under the same H2; a tiny leftover folds back into its parent/sibling if the result stays <=600 tokens. It never crosses an H2/H1 boundary, so a tiny H2 stays a small chunk. Effect: more small chunks than a boundary-blind merge. The first draft merged across boundaries (605 forward + 210 backward crossings measured); that was a bug.
- **Oversize** tables and code fences are split at line boundaries; table header (and separator) and fence markers repeat in each piece; prose uses `RecursiveCharacterTextSplitter` (600 target, 50 overlap). 800 tokens is enforced after the prefix; the run aborts if any chunk exceeds it.
- **Hugo `## {{% heading "x" %}}`** already contains the hashes; first draft doubled them (`## ## What's next`). Fixed.
- **22 section `_index.md` pages have no body** (front matter only), so they produce no chunks. They are still loaded (511 pages).
- **chunk_id** = sha256(doc_id, chunker, position, content)[:16] as in the guide. Position is in the hash, so inserting a chunk earlier in a doc changes the ids of later chunks (stable only for unchanged chunk sequences).
- **Embedding cache key (Phase 2, decided now)**: `sha256(embed_model + dims + exact_embedded_text)`, jsonl, not keyed by `chunk_id`. Deviation from "chunk hash + model": changing the heading-path prefix format, chunk size or model changes the text/model and so the key; unchanged text keeps its vector even if its position moved, and identical text shared by both chunkers is embedded once.
- **Leftover check**: "any `{{`, `}}`, `{%`, `<!--`" is not 0 because code (JSON, Go templates, Liquid) legitimately contains them; the run reports strict counts, counts outside code, and a shortcode-shaped count, with examples.
