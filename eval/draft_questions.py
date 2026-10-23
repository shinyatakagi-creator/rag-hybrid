"""python -m eval.draft_questions [--dry-run]

Drafts candidate golden-set questions of two types from sampled chunks, then STOPS for human review:
  conceptual (22): everyday words, no distinctive vocabulary from the passage
  mixed      (16): one exact term taken from the passage plus a conceptual aspect
(slightly more than the planned 20 / 15 so you can cut weak ones.) Output: eval/golden_drafts.jsonl and a review
table eval/golden_drafts.md. The `source_doc_id` of a draft is only a SUGGESTION for expected_doc_ids: the drafting
model saw one passage, so you decide the final expected docs, and no retrieval result is shown here on purpose.

Sampling is seeded and spread over concepts / tasks / reference with one chunk per page (see QUOTAS). Every draft is
checked with the shared overlap functions (eval/overlap.py) and flagged, never silently dropped.
"""
import argparse
import json
import os
import random
import re
from pathlib import Path

from dotenv import load_dotenv

from eval.overlap import FLAG_DISTINCTIVE, FLAG_RATIO, doc_frequency, flags_for, question_metrics  # noqa: F401 (re-exported for callers and tests)
from ingest.embed_cache import SpendGuard
from ingest.loaders import load_corpus
from rag.generate import CHARS_PER_TOKEN, cost_usd

SEED = 7
QUOTAS = {  # chunks to sample per type and top-level folder (pages: concepts 187, tasks 212, reference 103)
    "conceptual": {"concepts": 8, "tasks": 9, "reference": 5},
    "mixed": {"concepts": 5, "tasks": 5, "reference": 6},
}
MIN_TOK, MAX_TOK = 150, 600  # chunk size window: enough to hold a question, small enough to read
MAX_CODE_SHARE = 0.35  # skip chunks that are mostly fenced code
MAX_TABLE_SHARE = 0.4  # ... or mostly table rows
MAX_TOKENS = 1500  # drafting ceiling (thinking + JSON); the worst case charged to the spend guard
TYPICAL_OUTPUT_TOKENS = 400  # ASSUMPTION used only for the 'typical' cost line; the real cost is read from usage
EFFORT = "low"
OUT_JSONL, OUT_MD = "eval/golden_drafts.jsonl", "eval/golden_drafts.md"

_ENTITY = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|quot|amp|lt|gt|nbsp|apos);")
# generated field / metric listings: fine for exact-term and mixed questions, poor material for a conceptual question
CONCEPTUAL_EXCLUDE = ("reference/config-api/", "reference/instrumentation/metrics")
_FENCE = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$", re.S | re.M)
# a backticked exact term: --flag, camelCase / PascalCase name, snake_case, or hyphenated name
_IDENT = re.compile(r"`(--[a-z][a-z0-9-]{3,}|[A-Za-z][A-Za-z0-9]*[a-z][A-Z][A-Za-z0-9]*|[a-z][a-z0-9]*_[a-z0-9_]+|[a-z][a-z0-9]+(?:-[a-z0-9]+)+)`")

COMMON = """You write evaluation questions for a Kubernetes documentation search system. You are given ONE documentation passage.
- The question must be answerable from the passage alone; never ask about anything the passage does not say.
- Never copy a run of three or more consecutive words from the passage.
- Also write a short reference answer (1-3 sentences, under 60 words) that uses only the passage.
- Return JSON with keys question, reference_answer, exact_term."""
SYSTEM = {
    "conceptual": COMMON + """

Write ONE question that a user who has never read this page might ask and that this passage answers. Describe the idea in
everyday words. Do NOT use the passage's distinctive vocabulary: no flag names, field names, API kinds, command names,
and none of the words from the page or section title. If you must refer to a specific thing, describe what it does or is
for. Set exact_term to the empty string.""",
    "mixed": COMMON + """

Write ONE question that combines exactly ONE exact term taken verbatim from the passage (a flag, field, command, resource
kind, or error string; copy it character for character, it will be given to you in the list of candidates) with a
conceptual aspect described in everyday words. The question must contain that exact term exactly as written in the
passage. Apart from that one term, avoid the passage's distinctive vocabulary. Set exact_term to that term.""",
}
SCHEMA = {
    "type": "object",
    "properties": {"question": {"type": "string"}, "reference_answer": {"type": "string"}, "exact_term": {"type": "string"}},
    "required": ["question", "reference_answer", "exact_term"],
    "additionalProperties": False,
}


class InvalidDraft(ValueError):
    pass


# -- sampling ---------------------------------------------------------------------------------------
def top_folder(doc_id: str) -> str:
    return doc_id.split("/")[0]


def identifiers(content: str) -> list[str]:
    return list(dict.fromkeys(_IDENT.findall(content)))


def _share(content: str, kind: str) -> float:
    if kind == "code":
        return sum(len(m.group(0)) for m in _FENCE.finditer(content)) / max(len(content), 1)
    rows = [l for l in content.split("\n") if l.lstrip().startswith("|")]
    return sum(len(l) for l in rows) / max(len(content), 1)


def eligible(chunk: dict, need_identifier: bool, exclude_prefixes: tuple = ()) -> bool:
    c = chunk["content"]
    if not MIN_TOK <= chunk["token_count"] <= MAX_TOK or top_folder(chunk["doc_id"]) not in QUOTAS["conceptual"]:
        return False
    if chunk["doc_id"].startswith(exclude_prefixes) or _ENTITY.search(c) or _ENTITY.search(chunk["heading_path"]):
        return False  # entities: raw HTML in the chunk text (known loader gap, see NOTES.md); do not build a question on mangled text
    if _share(c, "code") > MAX_CODE_SHARE or _share(c, "table") > MAX_TABLE_SHARE:
        return False
    return bool(identifiers(c)) if need_identifier else True


def sample_chunks(chunks: list[dict], quota: dict[str, int], need_identifier: bool, used_docs: set[str], rng: random.Random,
                  exclude_prefixes: tuple = ()) -> list[dict]:
    """One chunk per page, spread over the folders in `quota`; deterministic for a given rng and chunk set."""
    pool = sorted((c for c in chunks if eligible(c, need_identifier, exclude_prefixes) and c["doc_id"] not in used_docs), key=lambda c: c["chunk_id"])
    rng.shuffle(pool)
    picked, per_folder = [], dict.fromkeys(quota, 0)
    for c in pool:
        f = top_folder(c["doc_id"])
        if per_folder[f] >= quota[f] or c["doc_id"] in used_docs:
            continue
        per_folder[f] += 1
        used_docs.add(c["doc_id"])
        picked.append(c)
    return picked


# -- prompt, validation, flags ------------------------------------------------------------------------
def user_message(chunk: dict, typ: str) -> str:
    msg = f"Passage (section: {chunk['heading_path']}):\n\n{chunk['content']}"
    if typ == "mixed":
        msg += "\n\nCandidate exact terms in this passage: " + ", ".join(identifiers(chunk["content"])[:12])
    return msg


def validate_draft(obj, typ: str, chunk_content: str) -> dict:
    if not isinstance(obj, dict) or set(obj) != {"question", "reference_answer", "exact_term"} or not all(isinstance(v, str) for v in obj.values()):
        raise InvalidDraft(f"expected string keys question, reference_answer, exact_term; got {obj!r}")
    q, a, t = obj["question"].strip(), obj["reference_answer"].strip(), obj["exact_term"].strip()
    if not 5 <= len(q.split()) <= 45:
        raise InvalidDraft(f"question length {len(q.split())} words outside 5-45")
    if not a or len(a) > 500:
        raise InvalidDraft("reference_answer empty or over 500 characters")
    if typ == "conceptual" and t:
        raise InvalidDraft(f"conceptual draft must have an empty exact_term, got {t!r}")
    if typ == "mixed":
        if not t:
            raise InvalidDraft("mixed draft needs an exact_term")
        if t not in chunk_content:
            raise InvalidDraft(f"exact_term {t!r} is not literally in the passage")
        if t not in q:
            raise InvalidDraft(f"exact_term {t!r} is not in the question")
    return {"question": q, "reference_answer": a, "exact_term": t}


def draft_metrics(draft: dict, typ: str, chunk_text: str, df, n_docs: int) -> dict:
    """Overlap numbers for a draft (shared implementation: eval.overlap.question_metrics, declared exact term taken out first)."""
    return question_metrics(draft["question"], draft["exact_term"], chunk_text, df, n_docs)


def estimate_one(model: str, typ: str, chunk: dict) -> dict:
    tin = int((len(SYSTEM[typ]) + len(user_message(chunk, typ))) / CHARS_PER_TOKEN)
    return {"input_tokens": tin, "typical": cost_usd(model, tin, TYPICAL_OUTPUT_TOKENS), "worst": cost_usd(model, tin, MAX_TOKENS)}


def draft_one(client, guard: SpendGuard, model: str, typ: str, chunk: dict, df, n_docs: int, chunk_text: str) -> dict:
    est = estimate_one(model, typ, chunk)
    guard.charge(est["worst"], f"drafting for {chunk['doc_id']}")
    resp = client.messages.create(
        model=model, max_tokens=MAX_TOKENS, system=SYSTEM[typ], messages=[{"role": "user", "content": user_message(chunk, typ)}],
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
    cost = cost_usd(model, **usage)
    guard.settle(est["worst"], cost)
    rec = {"type": typ, "source_doc_id": chunk["doc_id"], "source_chunk_id": chunk["chunk_id"], "source_heading_path": chunk["heading_path"],
           "source_url": chunk["url"], "model": model, "usage": usage, "cost_usd": cost}
    try:
        if resp.stop_reason != "end_turn":
            raise InvalidDraft(f"stop_reason={resp.stop_reason!r}")
        text = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise InvalidDraft(f"not JSON: {e}") from e
        d = validate_draft(obj, typ, chunk["content"])
    except InvalidDraft as e:
        return {**rec, "error": str(e)}
    m = draft_metrics(d, typ, chunk_text, df, n_docs)
    return {**rec, **d, "metrics": m, "flags": flags_for(m, typ)}


def render_md(drafts: list[dict]) -> str:
    out = ["# Golden-set drafts for review", "",
           "`source_doc` is only a suggestion for `expected_doc_ids`: the drafting model saw one passage. Pick the final pages from your own reading. "
           "Flagged = high word overlap with the source passage (the draft may flatter BM25).", ""]
    for d in drafts:
        flag = "  **FLAGGED**" if d.get("flags") else ""
        out.append(f"## {d['id']} · {d['type']}{flag}")
        if "error" in d:
            out += [f"- DRAFT FAILED: {d['error']}", f"- source: `{d['source_doc_id']}`", ""]
            continue
        out += [f"- **Q:** {d['question']}", f"- **Reference answer:** {d['reference_answer']}"]
        if d["exact_term"]:
            out.append(f"- exact term: `{d['exact_term']}`")
        out += [f"- source_doc (suggested expected): `{d['source_doc_id']}` · {d['source_url']}", f"- section: {d['source_heading_path']}",
                f"- overlap: ratio {d['metrics']['overlap_ratio']}, distinctive shared {d['metrics']['distinctive_shared']}, copied phrases {d['metrics']['copied_phrases']}"]
        if d["flags"]:
            out.append(f"- flags: {'; '.join(d['flags'])}")
        out.append("")
    return "\n".join(out)


def plan(chunks: list[dict]) -> list[tuple[str, dict]]:
    rng, used = random.Random(SEED), set()
    out = []
    for typ in ("conceptual", "mixed"):
        got = sample_chunks(chunks, QUOTAS[typ], typ == "mixed", used, rng, CONCEPTUAL_EXCLUDE if typ == "conceptual" else ())
        out += [(typ, c) for c in got]
        short = sum(QUOTAS[typ].values()) - len(got)
        if short:
            print(f"WARNING: {typ}: only {len(got)} of {sum(QUOTAS[typ].values())} chunks were eligible")
    return out


def main(argv=None) -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show the sample and the cost estimate; no API call")
    ap.add_argument("--chunks", default="data/chunks/heading.jsonl")
    ap.add_argument("--model", default=None, help="default ANSWER_MODEL")
    a = ap.parse_args(argv)
    model = a.model or os.environ["ANSWER_MODEL"]
    chunks = [json.loads(l) for l in open(a.chunks, encoding="utf8")]
    todo = plan(chunks)
    ests = [estimate_one(model, t, c) for t, c in todo]
    print(f"{'#':>3} {'type':10} {'folder':9} {'tok':>4}  doc_id | section")
    for i, ((t, c), e) in enumerate(zip(todo, ests), 1):
        print(f"{i:3d} {t:10} {top_folder(c['doc_id']):9} {c['token_count']:4d}  {c['doc_id']} | {c['heading_path'][-60:]}")
    tin, typ_cost, worst = sum(e["input_tokens"] for e in ests), sum(e["typical"] for e in ests), sum(e["worst"] for e in ests)
    print(f"\n{len(todo)} drafts with {model} (effort {EFFORT}): ~{tin:,} input tokens; typical cost ${typ_cost:.3f} "
          f"(assumes ~{TYPICAL_OUTPUT_TOKENS} output tokens each), worst case ${worst:.3f} (every call hits the {MAX_TOKENS}-token ceiling)")
    if a.dry_run:
        print("dry run: no API call made")
        return
    if input(f"Draft {len(todo)} questions? [y/N] ").strip().lower() != "y":
        print("cancelled")
        return
    import anthropic

    docs = load_corpus(Path("data/k8s"))
    text_of = {d.doc_id: d.title + "\n" + d.text for d in docs}
    df, n_docs = doc_frequency(list(text_of.values())), len(docs)
    guard, client = SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5"))), anthropic.Anthropic()
    drafts = []
    with open(OUT_JSONL, "w", encoding="utf8") as f:
        for i, (typ, c) in enumerate(todo, 1):
            # overlap is measured against the whole source page, not only the sampled chunk: the page is what retrieval can match
            d = {"id": f"d{i:03d}", **draft_one(client, guard, model, typ, c, df, n_docs, text_of[c["doc_id"]])}
            drafts.append(d)
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{d['id']} {typ:10} {'FAILED: ' + d['error'] if 'error' in d else ('FLAGGED ' if d['flags'] else 'ok      ') + d['question'][:90]}")
    Path(OUT_MD).write_text(render_md(drafts), encoding="utf8")
    ok = [d for d in drafts if "error" not in d]
    print(f"\n{len(ok)} drafts, {len(drafts) - len(ok)} failed, {sum(1 for d in ok if d['flags'])} flagged; spend ${guard.spent:.4f}")
    print(f"wrote {OUT_JSONL} and {OUT_MD}. STOPPING: review them and choose the expected_doc_ids.")


if __name__ == "__main__":
    main()
