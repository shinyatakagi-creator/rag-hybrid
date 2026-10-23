"""Answer generation with numbered citations.

    python -m rag.generate --question "..." [--dry-run]

Context = hybrid retrieval on the heading chunker, top 8 chunks with at most 2 per doc (a context cap only; the
retrieval itself is unchanged). The model returns structured JSON {answerable, sentences:[{sentence, citations}]}
which is validated in code before anyone sees it.
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from ingest.embed_cache import SpendGuard
from rag.retrieve import QueryEmbedder, hybrid

# USD per 1M tokens (input, output), standard pricing. Source: platform.claude.com/docs/en/about-claude/pricing,
# checked 2026-10-23. A model not listed is refused rather than guessed. Thinking tokens are part of output_tokens.
PRICES = {"claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}  # Haiku 5.5: prompts up to 100K tokens ($0.50 / $2.50 above)
MAX_CHUNKS, PER_DOC = 8, 2
RETRIEVE_K = 40  # fused candidates considered before the per-doc context cap
MAX_TOKENS = 4000  # ceiling for thinking + answer; also the worst case used for the spend guard
EFFORT = "medium"
CHARS_PER_TOKEN = 2.5  # docs: 1M tokens ~ 2.5M characters on the current tokenizer; used for estimates only
LOG_PATH = "eval/results/generation_log.jsonl"

SYSTEM = """You answer questions about Kubernetes using ONLY the numbered documentation excerpts the user provides.

Rules:
- Write the answer as a list of sentences. Every sentence that states a fact must list, in `citations`, the number(s) of the excerpt(s) that support it.
- Use only information that is in the excerpts. Do not add outside knowledge, even if you know it.
- Cite an excerpt only if it really supports that sentence. Never invent excerpt numbers.
- Do not write citation markers such as [1] inside the sentence text; put the numbers in `citations`.
- If the excerpts do not contain the answer, set `answerable` to false, return exactly one sentence saying the provided documentation does not cover the question, give it no citations, and stop. Do not guess and do not answer from memory."""

SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "sentences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"sentence": {"type": "string"}, "citations": {"type": "array", "items": {"type": "integer"}}},
                "required": ["sentence", "citations"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["answerable", "sentences"],
    "additionalProperties": False,
}


class InvalidAnswer(ValueError):
    pass


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in PRICES:
        raise ValueError(f"no verified price for {model!r}; add it to PRICES before calling it")
    pin, pout = PRICES[model]
    return input_tokens / 1e6 * pin + output_tokens / 1e6 * pout


def select_context(hits: list[dict], max_chunks: int = MAX_CHUNKS, per_doc: int = PER_DOC) -> list[dict]:
    """Walk the ranked hits, skip a chunk once its doc already has `per_doc`, stop at `max_chunks`."""
    out, count = [], {}
    for h in hits:
        if count.get(h["doc_id"], 0) >= per_doc:
            continue
        count[h["doc_id"]] = count.get(h["doc_id"], 0) + 1
        out.append(h)
        if len(out) == max_chunks:
            break
    return out


def build_user_message(question: str, chunks: list[dict]) -> str:
    excerpts = "\n\n".join(f"[{i}] {c['heading_path']}\nURL: {c['url']}\n{c['content']}" for i, c in enumerate(chunks, 1))
    return f"Documentation excerpts:\n\n{excerpts}\n\nQuestion: {question}"


def validate_answer(obj, n_chunks: int) -> dict:
    """Reject anything the schema cannot guarantee: out-of-range citations, uncited facts, a refusal that cites."""
    if not isinstance(obj, dict) or set(obj) != {"answerable", "sentences"}:
        raise InvalidAnswer(f"expected keys answerable+sentences, got {obj!r}")
    if not isinstance(obj["answerable"], bool) or not isinstance(obj["sentences"], list) or not obj["sentences"]:
        raise InvalidAnswer("answerable must be a bool and sentences a non-empty list")
    for i, s in enumerate(obj["sentences"], 1):
        if not isinstance(s, dict) or set(s) != {"sentence", "citations"}:
            raise InvalidAnswer(f"sentence {i}: expected keys sentence+citations")
        if not isinstance(s["sentence"], str) or not s["sentence"].strip():
            raise InvalidAnswer(f"sentence {i}: empty text")
        cites = s["citations"]
        if not isinstance(cites, list) or any(type(c) is not int for c in cites):
            raise InvalidAnswer(f"sentence {i}: citations must be a list of integers")
        bad = [c for c in cites if not 1 <= c <= n_chunks]
        if bad:
            raise InvalidAnswer(f"sentence {i}: citation(s) {bad} outside 1..{n_chunks}")
        if obj["answerable"] and not cites:
            raise InvalidAnswer(f"sentence {i}: factual sentence without a citation")
        if not obj["answerable"] and cites:
            raise InvalidAnswer(f"sentence {i}: a refusal must not cite")
    if not obj["answerable"] and len(obj["sentences"]) != 1:
        raise InvalidAnswer("a refusal must be exactly one sentence")
    return obj


def estimate(system: str, user: str, model: str) -> dict:
    tin = int((len(system) + len(user)) / CHARS_PER_TOKEN)
    return {
        "input_tokens_est": tin,
        "input_cost_est": cost_usd(model, tin, 0),
        "worst_case_output_tokens": MAX_TOKENS,
        "worst_case_cost": cost_usd(model, tin, MAX_TOKENS),
    }


def generate(client, guard: SpendGuard, model: str, question: str, chunks: list[dict], confirm=None, dry_run: bool = False,
             log_path: str | None = LOG_PATH) -> dict:
    user = build_user_message(question, chunks)
    est = estimate(SYSTEM, user, model)
    result = {"question": question, "model": model, "effort": EFFORT, "estimate": est,
              "chunks": [{"n": i, "chunk_id": c["chunk_id"], "doc_id": c["doc_id"], "heading_path": c["heading_path"], "url": c["url"],
                          "content": c["content"]}  # stored so a logged answer can be verified without the index
                         for i, c in enumerate(chunks, 1)]}
    if dry_run:
        return result
    if confirm and not confirm(est):
        raise SystemExit("cancelled")
    guard.charge(est["worst_case_cost"], "answer generation (worst case)")  # raises BudgetExceeded before any call
    t0 = time.time()
    resp = client.messages.create(
        model=model, max_tokens=MAX_TOKENS, system=SYSTEM, messages=[{"role": "user", "content": user}],
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    latency = time.time() - t0
    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
    actual = cost_usd(model, **usage)
    guard.settle(est["worst_case_cost"], actual)
    result.update(usage=usage, cost_usd=actual, latency_s=round(latency, 2), stop_reason=resp.stop_reason)
    try:
        if resp.stop_reason != "end_turn":
            raise InvalidAnswer(f"stop_reason={resp.stop_reason!r} (answer not complete)")
        text = next((b.text for b in resp.content if b.type == "text"), None)
        if text is None:
            raise InvalidAnswer("no text block in response")
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as e:
            raise InvalidAnswer(f"response is not JSON: {e}") from e
        result["answer"] = validate_answer(obj, len(chunks))
    except InvalidAnswer as e:
        result["error"] = str(e)
    if log_path:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf8") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **result}, ensure_ascii=False) + "\n")
    if "error" in result:
        raise InvalidAnswer(result["error"])
    return result


def retrieve_context(es, index: str, embedder: QueryEmbedder, question: str) -> list[dict]:
    hits = hybrid(es, index, question, embedder(question), "heading", k=RETRIEVE_K)
    return select_context(hits)


def main(argv=None) -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--dry-run", action="store_true", help="retrieve and print the cost estimate; no generation call")
    a = ap.parse_args(argv)
    import anthropic
    model = os.environ["ANSWER_MODEL"]
    emb_model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    guard = SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5")))

    def confirm_embed(what, tokens, usd):
        return input(f"Embed query ({tokens} tokens, est. ${usd:.8f})? [y/N] ").strip().lower() == "y"

    def openai_client():
        from openai import OpenAI
        return OpenAI(max_retries=0)

    emb = QueryEmbedder(f"data/embed_cache/{emb_model}.jsonl", emb_model, openai_client, guard, confirm=confirm_embed)
    es = Elasticsearch(os.environ.get("ES_URL", "http://127.0.0.1:9200"))
    chunks = retrieve_context(es, os.environ.get("ES_INDEX", "rag-docs"), emb, a.question)

    def confirm(est):
        return input(f"Generate with {model}: ~{est['input_tokens_est']} input tokens (est. ${est['input_cost_est']:.4f}), "
                     f"worst-case output {est['worst_case_output_tokens']} tokens; worst case ${est['worst_case_cost']:.4f}. Proceed? [y/N] "
                     ).strip().lower() == "y"

    r = generate(anthropic.Anthropic(), guard, model, a.question, chunks, confirm=confirm, dry_run=a.dry_run)
    print(f"\nQuestion: {a.question}\nContext ({len(chunks)} chunks):")
    for c in r["chunks"]:
        print(f"  [{c['n']}] {c['doc_id']} | {c['heading_path'][:90]}")
    e = r["estimate"]
    if a.dry_run:
        print(f"\nDRY RUN: ~{e['input_tokens_est']} input tokens = ${e['input_cost_est']:.4f}; worst-case output {e['worst_case_output_tokens']} tokens "
              f"-> worst case ${e['worst_case_cost']:.4f}. No generation call made.")
        return
    print("\nStructured answer:")
    print(json.dumps(r["answer"], indent=2, ensure_ascii=False))
    u = r["usage"]
    print(f"\nusage: input={u['input_tokens']} output={u['output_tokens']} tokens | cost=${r['cost_usd']:.6f} "
          f"(estimate was ~{e['input_tokens_est']} in) | latency={r['latency_s']}s | model={r['model']} effort={r['effort']}")
    print(f"logged to {LOG_PATH}")


if __name__ == "__main__":
    main()
