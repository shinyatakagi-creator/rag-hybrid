"""Citation verification: does each cited excerpt support the sentence it is attached to?

    python -m rag.verify --log eval/results/generation_log.jsonl [--rows 0,1,2] [--dry-run]

One batched call per answer to the Haiku-class model: every (sentence, cited chunk) pair gets yes / partial / no plus a
one-line reason, as structured output validated in code. A refusal has no citations, so there is nothing to verify.
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from ingest.embed_cache import SpendGuard
from rag.generate import CHARS_PER_TOKEN, PRICES, cost_usd

VERDICTS = ("yes", "partial", "no")
MAX_TOKENS = 3000
EFFORT = "low"
SNAPSHOT = "eval/results/context_snapshot.json"
LOG_PATH = "eval/results/verification_log.jsonl"

SYSTEM = """You check citations. You are given numbered documentation excerpts and numbered sentences; each sentence cites one or more excerpts. For EVERY (sentence, excerpt) pair listed, decide whether that excerpt supports the sentence.

- yes: the excerpt states, or directly implies, everything the sentence claims, including every specific number, name, condition and quantifier.
- partial: the excerpt supports part of the sentence, but the sentence also contains a claim, number, condition or generalisation that is not in the excerpt, or goes beyond what it says.
- no: the excerpt does not support the sentence, is about something else, or contradicts it.

Judge ONLY against the excerpt text provided. Do not use your own knowledge of Kubernetes, and do not give credit because the sentence happens to be true. Give a one-line reason (under 25 words) that names what is or is not in the excerpt. Return exactly one judgement per listed pair, no others."""

SCHEMA = {
    "type": "object",
    "properties": {
        "judgements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sentence": {"type": "integer"},
                    "citation": {"type": "integer"},
                    "verdict": {"type": "string", "enum": list(VERDICTS)},
                    "reason": {"type": "string"},
                },
                "required": ["sentence", "citation", "verdict", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["judgements"],
    "additionalProperties": False,
}


class InvalidVerdicts(ValueError):
    pass


def pairs_of(sentences: list[dict]) -> list[tuple[int, int]]:
    """(sentence number, citation) for every citation, sentences numbered from 1."""
    return [(i, c) for i, s in enumerate(sentences, 1) for c in dict.fromkeys(s["citations"])]


def build_message(sentences: list[dict], chunks: dict[int, str]) -> str:
    cited = sorted({c for s in sentences for c in s["citations"]})
    ex = "\n\n".join(f"[Excerpt {n}]\n{chunks[n]}" for n in cited)
    sents = "\n".join(f"Sentence {i}: {s['sentence']}  (cites excerpt(s) {', '.join(map(str, s['citations']))})" for i, s in enumerate(sentences, 1))
    pairs = "\n".join(f"- sentence {i} vs excerpt {c}" for i, c in pairs_of(sentences))
    return f"{ex}\n\n{sents}\n\nPairs to judge:\n{pairs}"


def validate_verdicts(obj, expected: list[tuple[int, int]]) -> list[dict]:
    """Exactly one well-formed judgement per expected pair: no missing, extra or duplicate pairs."""
    if not isinstance(obj, dict) or set(obj) != {"judgements"} or not isinstance(obj["judgements"], list):
        raise InvalidVerdicts(f"expected {{'judgements': [...]}}, got {obj!r}")
    seen = {}
    for j in obj["judgements"]:
        if not isinstance(j, dict) or set(j) != {"sentence", "citation", "verdict", "reason"}:
            raise InvalidVerdicts(f"malformed judgement {j!r}")
        if type(j["sentence"]) is not int or type(j["citation"]) is not int:
            raise InvalidVerdicts(f"sentence/citation must be integers: {j!r}")
        if j["verdict"] not in VERDICTS:
            raise InvalidVerdicts(f"verdict {j['verdict']!r} not in {VERDICTS}")
        if not isinstance(j["reason"], str) or not j["reason"].strip():
            raise InvalidVerdicts(f"empty reason for {j!r}")
        key = (j["sentence"], j["citation"])
        if key in seen:
            raise InvalidVerdicts(f"duplicate judgement for pair {key}")
        seen[key] = j
    missing, extra = [p for p in expected if p not in seen], [p for p in seen if p not in set(expected)]
    if missing or extra:
        raise InvalidVerdicts(f"pairs missing {missing}, unexpected {extra}")
    return [seen[p] for p in expected]


def summarize(sentences: list[dict], judgements: list[dict]) -> dict:
    """Citation precision = share of citations judged yes. A sentence is unsupported when none of its citations is a
    yes (all partial/no), and partially supported when its best verdict is partial."""
    by_s: dict[int, list[str]] = {}
    for j in judgements:
        by_s.setdefault(j["sentence"], []).append(j["verdict"])
    unsupported = [i for i, v in by_s.items() if "yes" not in v and "partial" not in v]
    partial_only = [i for i, v in by_s.items() if "yes" not in v and "partial" in v]
    n = len(judgements)
    return {
        "citations": n,
        "yes": sum(j["verdict"] == "yes" for j in judgements),
        "partial": sum(j["verdict"] == "partial" for j in judgements),
        "no": sum(j["verdict"] == "no" for j in judgements),
        "citation_precision": (sum(j["verdict"] == "yes" for j in judgements) / n) if n else None,
        "unsupported_sentences": [{"sentence": i, "text": sentences[i - 1]["sentence"]} for i in sorted(unsupported)],
        "partially_supported_sentences": [{"sentence": i, "text": sentences[i - 1]["sentence"]} for i in sorted(partial_only)],
    }


def estimate(model: str, system: str, user: str) -> dict:
    tin = int((len(system) + len(user)) / CHARS_PER_TOKEN)
    return {"input_tokens_est": tin, "input_cost_est": cost_usd(model, tin, 0), "worst_case_cost": cost_usd(model, tin, MAX_TOKENS)}


def verify_answer(client, guard: SpendGuard, model: str, sentences: list[dict], chunks: dict[int, str], dry_run: bool = False,
                  confirm=None) -> dict:
    """Verify one answer. `chunks` maps citation number -> excerpt text. Returns judgements, summary, usage, cost."""
    expected = pairs_of(sentences)
    if not expected:
        return {"pairs": 0, "note": "no citations (refusal): nothing to verify", "summary": summarize(sentences, [])}
    missing = sorted({c for _, c in expected} - set(chunks))
    if missing:
        raise InvalidVerdicts(f"no excerpt text for cited chunk(s) {missing}")
    user = build_message(sentences, chunks)
    est = estimate(model, SYSTEM, user)
    out = {"pairs": len(expected), "estimate": est}
    if dry_run:
        return out
    if confirm and not confirm(est):
        raise SystemExit("cancelled")
    guard.charge(est["worst_case_cost"], "verification (worst case)")
    t0 = time.time()
    resp = client.messages.create(
        model=model, max_tokens=MAX_TOKENS, system=SYSTEM, messages=[{"role": "user", "content": user}],
        output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
    actual = cost_usd(model, **usage)
    guard.settle(est["worst_case_cost"], actual)
    out.update(usage=usage, cost_usd=actual, latency_s=round(time.time() - t0, 2), stop_reason=resp.stop_reason)
    if resp.stop_reason != "end_turn":
        raise InvalidVerdicts(f"stop_reason={resp.stop_reason!r}; cost ${actual:.6f} was spent")
    text = next((b.text for b in resp.content if b.type == "text"), None)
    try:
        out["judgements"] = validate_verdicts(json.loads(text), expected)
    except (json.JSONDecodeError, TypeError) as e:
        raise InvalidVerdicts(f"verifier output is not valid JSON: {e}") from e
    out["summary"] = summarize(sentences, out["judgements"])
    return out


def load_row_chunks(row: dict, snapshot: dict) -> dict[int, str]:
    """Excerpt text for a generation-log row: stored in the row (newer rows) or in the frozen snapshot (older rows)."""
    return {c["n"]: c.get("content") or snapshot[c["chunk_id"]]["content"] for c in row["chunks"]}


def main(argv=None) -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="eval/results/generation_log.jsonl")
    ap.add_argument("--rows", default=None, help="comma-separated 0-based row indexes (default all)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    import anthropic
    model = os.environ["VERIFIER_MODEL"]
    guard = SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5")))
    rows = [json.loads(l) for l in open(a.log, encoding="utf8")]
    snap = json.loads(Path(SNAPSHOT).read_text())["chunks"] if Path(SNAPSHOT).exists() else {}
    idx = [int(x) for x in a.rows.split(",")] if a.rows else range(len(rows))
    client = None if a.dry_run else anthropic.Anthropic()
    total_est = 0.0
    for i in idx:
        row = rows[i]
        sentences = row["answer"]["sentences"]
        label = f"row {i}: {row['question'][:70]!r}"
        confirm = lambda est: input(f"Verify {label}: ~{est['input_tokens_est']} input tokens (est. ${est['input_cost_est']:.5f}), "
                                    f"worst case ${est['worst_case_cost']:.5f}. Proceed? [y/N] ").strip().lower() == "y"
        r = verify_answer(client, guard, model, sentences, load_row_chunks(row, snap), dry_run=a.dry_run, confirm=confirm)
        print(f"\n== {label}  ({r['pairs']} pairs)")
        if not r["pairs"]:
            print("   ", r["note"])
            continue
        if a.dry_run:
            total_est += r["estimate"]["input_cost_est"]
            print(f"    DRY RUN: ~{r['estimate']['input_tokens_est']} input tokens = ${r['estimate']['input_cost_est']:.5f}; worst case ${r['estimate']['worst_case_cost']:.5f}")
            continue
        for j in r["judgements"]:
            print(f"    s{j['sentence']} vs [{j['citation']}]: {j['verdict'].upper():7} {j['reason']}")
        s = r["summary"]
        print(f"    citation precision {s['yes']}/{s['citations']} = {s['citation_precision']:.2f} (partial {s['partial']}, no {s['no']}); "
              f"unsupported sentences: {[u['sentence'] for u in s['unsupported_sentences']]}; partial-only: {[u['sentence'] for u in s['partially_supported_sentences']]}")
        print(f"    usage in={r['usage']['input_tokens']} out={r['usage']['output_tokens']} cost=${r['cost_usd']:.6f} latency={r['latency_s']}s")
        Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf8") as f:
            f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "source": a.log, "row": i, "question": row["question"], "model": model,
                                "effort": EFFORT, **{k: v for k, v in r.items() if k != "estimate"}}, ensure_ascii=False) + "\n")
    if a.dry_run:
        print(f"\nDRY RUN total (input only): ${total_est:.5f}. No API call made.")
    else:
        print(f"\nspend this run: ${guard.spent:.6f}")


if __name__ == "__main__":
    main()
