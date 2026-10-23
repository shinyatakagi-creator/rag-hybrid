"""Correctness check of the answer_eval answers against the golden reference answers (pre-registered before any run).

    python -m eval.correctness_check --dry-run     # cost estimate, no API call
    python -m eval.correctness_check --yes         # run, after the owner approved the estimate
    python -m eval.correctness_check --report-only # rebuild the report and review table from the saved log

For every ANSWERED, gold-answerable question of each config (one Haiku call per answer) the verifier model returns, as validated
structured output:  key_facts_covered = yes | partial | no   (does the answer state the key facts of the reference answer?)
                    contradicts_reference = yes | no          (does any statement in the answer conflict with the reference?)
plus a one-line reason. The judge sees the question, the reference answer and the answer text (no citations, no excerpts, no
verifier verdicts). The reference answers were written from the expected pages (some with quoted page sentences); the check
measures agreement with them, not truth. Review table: every answer that is not (covered yes and no contradiction) plus a seeded
random sample of the others, for the owner's spot-check. Logs: eval/results/correctness_log.jsonl (resumable).
"""
import argparse
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from eval.answer_eval import CONFIGS, GEN_LOG, read_log
from eval.retrieval_eval import git_info, load_golden
from ingest.embed_cache import SpendGuard
from rag.generate import CHARS_PER_TOKEN, cost_usd

COVERED = ("yes", "partial", "no")
CONTRADICTS = ("yes", "no")
MAX_TOKENS = 1500
EFFORT = "low"
LOG = "eval/results/correctness_log.jsonl"
OUT = "eval/results/correctness_check"
REVIEW = "eval/results/correctness_review.md"
SAMPLE_OK = 6   # random fully-correct answers added to the review table
SEED = 4

SYSTEM = """You grade an answer to a Kubernetes documentation question against a reference answer. The reference answer was written by a person from the documentation page(s) and states the key facts the answer should contain.

Return two judgements:
1. key_facts_covered:
   - yes: the answer states all the key facts of the reference answer. Paraphrase, different wording and equivalent numbers or names count as stating them. Extra correct detail not in the reference is fine.
   - partial: the answer states some but not all of the key facts.
   - no: the answer states none of the key facts, or answers a different question.
2. contradicts_reference:
   - yes: some statement in the answer is incompatible with the reference answer (a different value, a different component, the opposite behaviour).
   - no: nothing in the answer conflicts with the reference. Detail the reference does not mention is not a contradiction.

Judge ONLY against the reference answer. Do not use your own knowledge of Kubernetes and do not give credit or blame because something is true or false in general. Add a one-line reason (under 30 words) naming the decisive point."""

SCHEMA = {
    "type": "object",
    "properties": {"key_facts_covered": {"type": "string", "enum": list(COVERED)}, "contradicts_reference": {"type": "string", "enum": list(CONTRADICTS)}, "reason": {"type": "string"}},
    "required": ["key_facts_covered", "contradicts_reference", "reason"],
    "additionalProperties": False,
}


class InvalidJudgement(ValueError):
    usage: dict | None = None
    cost_usd: float | None = None


def build_message(question: str, reference: str, answer_sentences: list[dict]) -> str:
    return f"Question: {question}\n\nReference answer: {reference}\n\nAnswer to grade:\n" + " ".join(s["sentence"] for s in answer_sentences)


def validate(obj) -> dict:
    if not isinstance(obj, dict) or set(obj) != {"key_facts_covered", "contradicts_reference", "reason"}:
        raise InvalidJudgement(f"expected exactly key_facts_covered, contradicts_reference, reason; got {obj!r}")
    if obj["key_facts_covered"] not in COVERED or obj["contradicts_reference"] not in CONTRADICTS:
        raise InvalidJudgement(f"value outside the allowed enums: {obj!r}")
    if not isinstance(obj["reason"], str) or not obj["reason"].strip():
        raise InvalidJudgement("empty reason")
    return obj


def is_clean(j: dict) -> bool:
    return j["key_facts_covered"] == "yes" and j["contradicts_reference"] == "no"


def review_selection(rows: list[dict], n_ok: int = SAMPLE_OK, seed: int = SEED) -> list[dict]:
    """Every judged answer that is not clean (partial/no coverage or a contradiction), plus `n_ok` seeded random clean ones."""
    bad = [r for r in rows if not is_clean(r)]
    ok = sorted([r for r in rows if is_clean(r)], key=lambda r: (r["config"], r["qid"]))
    random.Random(seed).shuffle(ok)
    return sorted(bad + ok[:n_ok], key=lambda r: (r["qid"], r["config"]))


def judge(client, guard, model, question, reference, sentences) -> dict:
    user = build_message(question, reference, sentences)
    worst = cost_usd(model, int((len(SYSTEM) + len(user)) / CHARS_PER_TOKEN), MAX_TOKENS)
    guard.charge(worst, "correctness check (worst case)")
    t0 = time.time()
    resp = client.messages.create(model=model, max_tokens=MAX_TOKENS, system=SYSTEM, messages=[{"role": "user", "content": user}],
                                  output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}})
    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
    actual = cost_usd(model, **usage)
    guard.settle(worst, actual)
    try:
        if resp.stop_reason != "end_turn":
            raise InvalidJudgement(f"stop_reason={resp.stop_reason!r}")
        text = next((b.text for b in resp.content if b.type == "text"), None)
        try:
            j = validate(json.loads(text))
        except (json.JSONDecodeError, TypeError) as e:
            raise InvalidJudgement(f"not valid JSON: {e}") from e
    except InvalidJudgement as e:
        e.usage, e.cost_usd = usage, actual
        raise
    return {**j, "usage": usage, "cost_usd": actual, "latency_s": round(time.time() - t0, 2)}


def targets(golden, gens) -> list[dict]:
    out = []
    for config in CONFIGS:
        for q in golden:
            g = gens.get((config, q["id"]))
            if q["answerable"] and g and "answer" in g and g["answer"]["answerable"]:
                out.append({"config": config, "qid": q["id"], "type": q["type"], "question": q["question"], "reference": q["reference_answer"], "sentences": g["answer"]["sentences"]})
    return out


def main(argv=None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args(argv)
    model = os.environ["VERIFIER_MODEL"]
    golden = load_golden("eval/golden.jsonl")
    gens = read_log(GEN_LOG, lambda r: (r["config"], r["qid"]))
    ts = targets(golden, gens)
    done = read_log(LOG, lambda r: (r["config"], r["qid"]))
    if a.dry_run:
        todo = [t for t in ts if (t["config"], t["qid"]) not in done]
        tin = [int((len(SYSTEM) + len(build_message(t["question"], t["reference"], t["sentences"]))) / CHARS_PER_TOKEN) for t in todo]
        typ_out = 90  # assumption: two enums + a one-line reason; the real figure comes from usage
        print(f"correctness check: {len(todo)} answered answerable (config, question) pairs ({', '.join(f'{c} {sum(t['config'] == c for t in todo)}' for c in CONFIGS)}), model {model}, effort {EFFORT}\n"
              f"input ~{sum(tin)} tokens total (~{sum(tin) // len(tin)} per call, chars/{CHARS_PER_TOKEN}); typical output assumed {typ_out} tokens per call\n"
              f"typical cost ${cost_usd(model, sum(tin), typ_out * len(todo)):.4f}; worst case (every call at the {MAX_TOKENS}-token ceiling) ${cost_usd(model, sum(tin), MAX_TOKENS * len(todo)):.4f}; "
              f"MAX_SPEND_USD=${os.environ.get('MAX_SPEND_USD', '5')}. No API call made.")
        return 0
    if not a.report_only:
        if not a.yes:
            print("refusing to call the API without --yes (dry-run first)")
            return 2
        import anthropic
        client, guard = anthropic.Anthropic(), SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5")))
        for t in ts:
            if (t["config"], t["qid"]) in done:
                continue
            rec = {"ts": datetime.now(timezone.utc).isoformat(), "config": t["config"], "qid": t["qid"], "type": t["type"], "model": model, "effort": EFFORT}
            try:
                rec.update(judge(client, guard, model, t["question"], t["reference"], t["sentences"]))
            except InvalidJudgement as e:
                rec.update(error=str(e), usage=e.usage, cost_usd=e.cost_usd)
            with open(LOG, "a", encoding="utf8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"{t['config']} {t['qid']}: " + (rec.get("error") or f"covered={rec['key_facts_covered']} contradicts={rec['contradicts_reference']}") + f" (spent ${guard.spent:.5f})")
        done = read_log(LOG, lambda r: (r["config"], r["qid"]))
    report(ts, done, model)
    return 0


def report(ts, done, model) -> None:
    by = {(t["config"], t["qid"]): t for t in ts}
    judged = [{**by[k], **v} for k, v in done.items() if k in by and "error" not in v]
    errors = [k for k, v in done.items() if "error" in v]
    summ = {}
    for c in CONFIGS:
        rs = [r for r in judged if r["config"] == c]
        n = len(rs)
        summ[c] = {"answered_judged": n, "errors": sum(k[0] == c for k in errors), "covered_yes": sum(r["key_facts_covered"] == "yes" for r in rs),
                   "covered_partial": sum(r["key_facts_covered"] == "partial" for r in rs), "covered_no": sum(r["key_facts_covered"] == "no" for r in rs),
                   "contradicts": sum(r["contradicts_reference"] == "yes" for r in rs), "clean": sum(is_clean(r) for r in rs)}
    sel = review_selection(judged)
    cost = sum(v.get("cost_usd") or 0 for v in done.values())
    doc = {"meta": {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git": git_info(), "judge_model": model, "effort": EFFORT, "max_tokens": MAX_TOKENS,
                    "prompt": SYSTEM, "schema": SCHEMA, "cost_usd": round(cost, 6), "review_sample": {"clean_sampled": SAMPLE_OK, "seed": SEED}}, "summary": summ,
           "judgements": [{k: r[k] for k in ("config", "qid", "type", "key_facts_covered", "contradicts_reference", "reason")} for r in judged], "errors": [list(k) for k in errors]}
    Path(OUT + ".json").write_text(json.dumps(doc, indent=1))
    L = ["# Correctness check", "", f"Judge `{model}` (effort {EFFORT}); cost ${cost:.4f}. Pre-registered; the judge sees the question, the reference answer and the answer text only. "
         "It measures agreement with the reference answers, which were written from the expected pages; it is not an independent truth check, and the judge itself is unvalidated.", "",
         "| config | answers judged | covered yes | partial | no | contradicts reference | clean (yes and no contradiction) | errors |", "|---|---|---|---|---|---|---|---|"]
    for c, s in summ.items():
        L.append(f"| {c} | {s['answered_judged']} | {s['covered_yes']} | {s['covered_partial']} | {s['covered_no']} | {s['contradicts']} | {s['clean']} | {s['errors']} |")
    Path(OUT + ".md").write_text("\n".join(L) + "\n", encoding="utf8")
    R = ["# Correctness review table", "", f"Every answer that is not clean plus {SAMPLE_OK} random clean ones (seed {SEED}), for the owner's spot-check. Verdict = key facts covered / contradicts reference. Marked `random clean` rows are the sampled ones.", ""]
    for r in sel:
        tag = "random clean" if is_clean(r) else "not clean"
        R += [f"## {r['qid']} / {r['config']} ({r['type']}) [{tag}]", "", f"**Question:** {r['question']}", "", f"**Reference:** {r['reference']}", "",
              f"**Answer:** {' '.join(s['sentence'] for s in r['sentences'])}", "", f"**Verdict:** covered = {r['key_facts_covered']}, contradicts = {r['contradicts_reference']}", "", f"**Reason:** {r['reason']}", ""]
    Path(REVIEW).write_text("\n".join(R), encoding="utf8")
    print(f"saved {OUT}.json/.md and {REVIEW} ({len(sel)} rows to review)")


if __name__ == "__main__":
    raise SystemExit(main())
