"""Answer eval on the frozen golden set (30 questions), two pre-registered configs:

    heading/hybrid  (Python RRF, dense weight 1)   and   heading/dense
    context = top 8 chunks, at most 2 per doc (rag.generate.select_context); answers by ANSWER_MODEL (structured, cited);
    every cited (sentence, excerpt) pair verified by VERIFIER_MODEL with the claims-v2 rubric (verdict derived in code).

    python -m eval.answer_eval --dry-run     # cost estimate, no API call (retrieval only)
    python -m eval.answer_eval --yes         # run, after the owner approved the estimate

Metrics (defined before any run):
  * faithfulness, over sentences of valid non-refusal answers: STRICT = share of sentences with at least one cited excerpt
    judged `yes`; LENIENT = share with at least one `yes` or `partial`. Reported for all answered questions and for gold-
    answerable questions only.
  * citation precision = share of (sentence, citation) pairs judged `yes`.
  * correct refusals = unanswerable questions (4) where the model refused; false refusals = answerable questions (26) where it refused;
    `answered_unanswerable` = unanswerable questions where it answered anyway (reported, never hidden).
  * invalid answers / verification errors are counted and reported, never dropped silently.
  * context coverage (diagnostic, no API): share of answerable questions whose context holds at least one expected doc.
Generation and verification logs are appended to eval/results/answer_eval_*.jsonl and make a rerun resumable (no double spend).
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from eval.retrieval_eval import TYPES, git_info, load_golden
from ingest.embed_cache import SpendGuard, cost_usd as embed_cost
from rag import generate as G
from rag import verify as V
from rag.retrieve import QueryEmbedder, dense, hybrid

CONFIGS = {"heading/hybrid": "hybrid", "heading/dense": "dense"}  # dense weight 1 for hybrid (pre-registered)
GEN_LOG = "eval/results/answer_eval_generation.jsonl"
VER_LOG = "eval/results/answer_eval_verification.jsonl"
OUT = "eval/results/answer_eval"


# -- pure metric helpers (unit-tested) -----------------------------------------------------------
def best_verdict_per_sentence(judgements: list[dict]) -> dict[int, str]:
    order = {"yes": 2, "partial": 1, "no": 0}
    best: dict[int, str] = {}
    for j in judgements:
        if j["sentence"] not in best or order[j["verdict"]] > order[best[j["sentence"]]]:
            best[j["sentence"]] = j["verdict"]
    return best


def faithfulness(per_question: list[dict]) -> dict:
    """per_question rows carry `sentence_verdicts` (best verdict per sentence) and `pair_verdicts` (one per citation)."""
    s = [v for q in per_question for v in q["sentence_verdicts"]]
    p = [v for q in per_question for v in q["pair_verdicts"]]
    n = len(s)
    return {"questions": len(per_question), "sentences": n, "strict": (sum(v == "yes" for v in s) / n) if n else None,
            "lenient": (sum(v in ("yes", "partial") for v in s) / n) if n else None, "citations": len(p),
            "citation_precision": (sum(v == "yes" for v in p) / len(p)) if p else None}


def summarize_config(rows: list[dict]) -> dict:
    """rows: one per golden question for a config: id, type, answerable (gold), outcome in {answered, refused, invalid},
    sentence_verdicts, pair_verdicts, verify_error, context_has_expected."""
    ans = [r for r in rows if r["answerable"]]
    un = [r for r in rows if not r["answerable"]]
    verified = [r for r in rows if r["outcome"] == "answered" and not r["verify_error"]]
    out = {"n_questions": len(rows), "n_answerable": len(ans), "n_unanswerable": len(un),
           "correct_refusals": sum(r["outcome"] == "refused" for r in un), "answered_unanswerable": sum(r["outcome"] == "answered" for r in un),
           "false_refusals": sum(r["outcome"] == "refused" for r in ans), "invalid_answers": sum(r["outcome"] == "invalid" for r in rows),
           "verification_errors": sum(r["outcome"] == "answered" and bool(r["verify_error"]) for r in rows),
           "context_has_expected": f"{sum(bool(r['context_has_expected']) for r in ans)} of {len(ans)}",
           "faithfulness_all_answered": faithfulness(verified),
           "faithfulness_answerable_only": faithfulness([r for r in verified if r["answerable"]]), "by_type": {}}
    for t in TYPES:
        rt = [r for r in ans if r["type"] == t]
        vt = [r for r in verified if r["type"] == t]
        out["by_type"][t] = {"n": len(rt), "false_refusals": sum(r["outcome"] == "refused" for r in rt), "invalid": sum(r["outcome"] == "invalid" for r in rt),
                             "faithfulness": faithfulness(vt)}
    return out


# -- run ---------------------------------------------------------------------------------------------------
def read_log(path: str, key) -> dict:
    p = Path(path)
    return {key(r): r for r in (json.loads(l) for l in p.read_text(encoding="utf8").splitlines() if l.strip())} if p.exists() else {}


def context_for(es, index, emb, question: str, mode: str) -> list[dict]:
    vec = emb(question)
    hits = hybrid(es, index, question, vec, "heading", k=G.RETRIEVE_K) if mode == "hybrid" else dense(es, index, vec, "heading", size=G.RETRIEVE_K)
    return G.select_context(hits)


def dry_run(golden, es, index, emb, model_a, model_v) -> int:
    earlier = [json.loads(l) for l in open("eval/results/generation_log.jsonl", encoding="utf8")]
    out_ans = [r["usage"]["output_tokens"] for r in earlier if r["answer"]["answerable"]]
    out_ref = [r["usage"]["output_tokens"] for r in earlier if not r["answer"]["answerable"]]
    ev = [json.loads(l) for l in open("eval/results/verification_log.jsonl", encoding="utf8") if '"claims-v2"' in l]
    v_in, v_out = sum(r["usage"]["input_tokens"] for r in ev) / len(ev), sum(r["usage"]["output_tokens"] for r in ev) / len(ev)
    uncached = [q for q in golden if not emb.is_cached(q["question"])]
    ins = []
    for q in golden:
        if q in uncached:
            continue
        for mode in CONFIGS.values():
            ch = context_for(es, index, emb, q["question"], mode)
            ins.append(G.estimate(G.SYSTEM, G.build_user_message(q["question"], ch), model_a)["input_tokens_est"])
    mean_in = sum(ins) / len(ins)
    n_gen = len(golden) * len(CONFIGS)
    n_un = sum(not q["answerable"] for q in golden) * len(CONFIGS)
    gen_in = sum(ins) + mean_in * len(uncached) * len(CONFIGS)
    typ_out = (n_gen - n_un) * (sum(out_ans) / len(out_ans)) + n_un * (sum(out_ref) / len(out_ref))
    gen_typ = G.cost_usd(model_a, int(gen_in), int(typ_out))
    gen_worst = G.cost_usd(model_a, int(gen_in), n_gen * G.MAX_TOKENS)
    n_ver = (len(golden) - sum(not q["answerable"] for q in golden)) * len(CONFIGS)  # answerable questions, if all are answered
    ver_typ = G.cost_usd(model_v, int(n_ver * v_in), int(n_ver * v_out))
    ver_worst = G.cost_usd(model_v, int(n_ver * v_in), n_ver * V.MAX_TOKENS)
    emb_tokens = sum(emb.estimate(q["question"])[0] for q in uncached)
    print(f"answer_eval dry run: {len(golden)} questions x {len(CONFIGS)} configs = {n_gen} generations ({model_a}, effort {G.EFFORT}); verification {model_v} ({V.RUBRIC}, effort {V.EFFORT})\n"
          f"retrieval-only for {len(golden) - len(uncached)} cached questions; {len(uncached)} unanswerable questions are not in the embedding cache "
          f"({[q['id'] for q in uncached]}): query embedding {emb_tokens} tokens, ${embed_cost(emb.model, emb_tokens):.8f}\n"
          f"mean generation input (est. chars/{G.CHARS_PER_TOKEN}) {mean_in:.0f} tokens; uncached questions assumed at the mean\n"
          f"typical output assumed from the 4 earlier answers: {sum(out_ans) / len(out_ans):.0f} tokens per answer, {sum(out_ref) / len(out_ref):.0f} per refusal\n"
          f"verification: up to {n_ver} calls, per call mean {v_in:.0f} in / {v_out:.0f} out tokens from the 4 earlier v2 calls\n\n"
          f"| step | typical | worst case |\n|---|---|---|\n| generation ({n_gen} calls) | ${gen_typ:.3f} | ${gen_worst:.3f} (every call at the {G.MAX_TOKENS}-token ceiling) |\n"
          f"| verification (<= {n_ver} calls) | ${ver_typ:.3f} | ${ver_worst:.3f} |\n| query embeddings | ${embed_cost(emb.model, emb_tokens):.8f} | same |\n"
          f"| **total** | **${gen_typ + ver_typ:.3f}** | **${gen_worst + ver_worst:.3f}** |\n\n"
          f"MAX_SPEND_USD=${os.environ.get('MAX_SPEND_USD', '5')} per run; spend so far about $0.29 (STATUS.md). No API call made.")
    return 0


def main(argv=None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", default="eval/golden.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="the owner approved the estimate")
    ap.add_argument("--retry-failed-verification", action="store_true", help="re-verify answers whose latest verification row is an error (one more attempt each; the failed rows stay in the log)")
    ap.add_argument("--report-only", action="store_true", help="rebuild eval/results/answer_eval.{json,md} from the saved logs; no API call")
    ap.add_argument("--ids", help="comma-separated question ids (a restricted run; the report then covers only those)")
    a = ap.parse_args(argv)
    golden = load_golden(a.golden)
    if a.ids:
        golden = [q for q in golden if q["id"] in set(a.ids.split(","))]
    model_a, model_v = os.environ["ANSWER_MODEL"], os.environ["VERIFIER_MODEL"]
    emb_model = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    index = os.environ.get("ES_INDEX", "rag-docs")
    guard = SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5")))

    def confirm_embed(what, tokens, usd):
        print(f"embedding {what}: {tokens} tokens, est. ${usd:.8f}")
        return a.yes or input("go ahead? [y/N] ").strip().lower() == "y"

    def openai_client():
        from openai import OpenAI
        return OpenAI(max_retries=0)

    emb = QueryEmbedder(f"data/embed_cache/{emb_model}.jsonl", emb_model, openai_client, guard, confirm=confirm_embed)
    es = Elasticsearch(os.environ.get("ES_URL", "http://127.0.0.1:9200"))
    if a.dry_run:
        return dry_run(golden, es, index, emb, model_a, model_v)
    if a.report_only:
        report(golden, read_log(GEN_LOG, lambda r: (r["config"], r["qid"])), read_log(VER_LOG, lambda r: (r["config"], r["qid"])), model_a, model_v)
        return 0
    if not a.yes:
        print("refusing to call paid APIs without --yes (run --dry-run first and get the estimate approved)")
        return 2
    import anthropic
    client = anthropic.Anthropic()
    if a.retry_failed_verification:
        return retry_failed(client, guard, model_v, golden)
    emb.prefetch([q["question"] for q in golden])
    gens = read_log(GEN_LOG, lambda r: (r["config"], r["qid"]))
    vers = read_log(VER_LOG, lambda r: (r["config"], r["qid"]))
    for config, mode in CONFIGS.items():
        for q in golden:
            key = (config, q["id"])
            ctx = context_for(es, index, emb, q["question"], mode)
            if key not in gens:
                try:
                    G.generate(client, guard, model_a, q["question"], ctx, log_path=GEN_LOG, extra={"config": config, "qid": q["id"], "type": q["type"], "gold_answerable": q["answerable"]})
                except G.InvalidAnswer:
                    pass  # logged with its error and usage by generate()
                gens = read_log(GEN_LOG, lambda r: (r["config"], r["qid"]))
            row = gens[key]
            if "answer" in row and row["answer"]["answerable"] and key not in vers:
                rec = {"ts": datetime.now(timezone.utc).isoformat(), "config": config, "qid": q["id"], "model": model_v, "effort": V.EFFORT, "rubric": V.RUBRIC}
                try:
                    r = V.verify_answer(client, guard, model_v, row["answer"]["sentences"], {c["n"]: c["content"] for c in row["chunks"]})
                    rec.update({k: v for k, v in r.items() if k != "estimate"})
                except V.InvalidVerdicts as e:
                    rec.update(error=str(e), usage=e.usage, cost_usd=e.cost_usd)
                with open(VER_LOG, "a", encoding="utf8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                vers = read_log(VER_LOG, lambda r: (r["config"], r["qid"]))
            print(f"{config} {q['id']}: " + ("refused" if "answer" in row and not row["answer"]["answerable"] else "invalid" if "answer" not in row else "answered"), f"(spent this run ${guard.spent:.4f})")
    report(golden, gens, vers, model_a, model_v)
    return 0


def retry_failed(client, guard, model_v, golden) -> int:
    """One more verification attempt for every answer whose latest verification row is an error. The failed row stays in
    the log; the new row (attempt 2) comes after it and is the one the report uses. A second failure is logged as well."""
    gens = read_log(GEN_LOG, lambda r: (r["config"], r["qid"]))
    vers = read_log(VER_LOG, lambda r: (r["config"], r["qid"]))
    for key, v in vers.items():
        if "error" not in v or v.get("attempt", 1) >= 2:
            continue
        config, qid = key
        g = gens[key]
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "config": config, "qid": qid, "model": model_v, "effort": V.EFFORT, "rubric": V.RUBRIC, "attempt": 2,
               "retry_of_error": v["error"]}
        try:
            r = V.verify_answer(client, guard, model_v, g["answer"]["sentences"], {c["n"]: c["content"] for c in g["chunks"]})
            rec.update({k: x for k, x in r.items() if k != "estimate"})
        except V.InvalidVerdicts as e:
            rec.update(error=str(e), usage=e.usage, cost_usd=e.cost_usd)
        with open(VER_LOG, "a", encoding="utf8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"retry {config} {qid}: " + ("failed again: " + rec["error"] if "error" in rec else f"ok, {len(rec['judgements'])} judgements") + f" (spent ${guard.spent:.6f})")
    report(golden, gens, read_log(VER_LOG, lambda r: (r["config"], r["qid"])), os.environ["ANSWER_MODEL"], model_v)
    return 0


def report(golden, gens, vers, model_a, model_v) -> None:
    configs = {}
    for config in CONFIGS:
        rows = []
        for q in golden:
            g, v = gens[(config, q["id"])], vers.get((config, q["id"]))
            outcome = "invalid" if "answer" not in g else ("answered" if g["answer"]["answerable"] else "refused")
            ctx_docs = {c["doc_id"] for c in g["chunks"]}
            judgements = (v or {}).get("judgements", [])
            rows.append({"id": q["id"], "type": q["type"], "answerable": q["answerable"], "outcome": outcome,
                         "sentence_verdicts": list(best_verdict_per_sentence(judgements).values()), "pair_verdicts": [j["verdict"] for j in judgements],
                         "verify_error": outcome == "answered" and (v is None or "error" in v), "context_has_expected": bool(set(q["expected_doc_ids"]) & ctx_docs),
                         "n_sentences": len(g["answer"]["sentences"]) if "answer" in g else 0, "error": g.get("error")})
        configs[config] = {"summary": summarize_config(rows), "questions": rows}
    cost = sum(r.get("cost_usd", 0) for r in gens.values()) + sum(r.get("cost_usd", 0) for r in vers.values())
    doc = {"meta": {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git": git_info(), "answer_model": model_a, "verifier_model": model_v,
                    "rubric": V.RUBRIC, "answer_effort": G.EFFORT, "verifier_effort": V.EFFORT, "context": {"chunker": "heading", "max_chunks": G.MAX_CHUNKS, "per_doc": G.PER_DOC,
                    "retrieve_k": G.RETRIEVE_K, "hybrid_dense_weight": 1}, "cost_usd_from_logs": round(cost, 6), "logs": [GEN_LOG, VER_LOG]}, "configs": configs}
    Path(OUT + ".json").write_text(json.dumps(doc, indent=1))
    L = ["# Answer eval", "", f"Git `{doc['meta']['git']['sha'][:7]}` | {doc['meta']['timestamp']} | answers `{model_a}` (effort {G.EFFORT}), verifier `{model_v}` ({V.RUBRIC}, effort {V.EFFORT}) | cost from logs ${cost:.4f}", "",
         "Faithfulness strict = sentences with at least one cited excerpt judged yes; lenient = yes or partial. Citation precision = share of cited pairs judged yes. "
         "The verifier's own accuracy is not established until the checkpoint-4 hand labels.", "",
         "| config | answered / refused / invalid | correct refusals (of 4) | answered unanswerable | false refusals (of 26) | faithfulness strict | lenient | citation precision | sentences |", "|---|---|---|---|---|---|---|---|---|"]
    for c, d in configs.items():
        s = d["summary"]
        f = s["faithfulness_all_answered"]
        pct = lambda x: "-" if x is None else f"{x:.3f}"
        L.append(f"| {c} | {sum(r['outcome'] == 'answered' for r in d['questions'])} / {sum(r['outcome'] == 'refused' for r in d['questions'])} / {s['invalid_answers']} | {s['correct_refusals']} | "
                 f"{s['answered_unanswerable']} | {s['false_refusals']} | {pct(f['strict'])} | {pct(f['lenient'])} | {pct(f['citation_precision'])} | {f['sentences']} |")
    L += ["", "Answerable questions only:", "", "| config | questions | strict | lenient | citation precision | context holds an expected doc |", "|---|---|---|---|---|---|"]
    for c, d in configs.items():
        f = d["summary"]["faithfulness_answerable_only"]
        L.append(f"| {c} | {f['questions']} | {f['strict']:.3f} | {f['lenient']:.3f} | {f['citation_precision']:.3f} | {d['summary']['context_has_expected']} |")
    L += ["", "By type:", "", "| config | type | n | false refusals | strict | lenient |", "|---|---|---|---|---|---|"]
    for c, d in configs.items():
        for t, b in d["summary"]["by_type"].items():
            L.append(f"| {c} | {t} | {b['n']} | {b['false_refusals']} | {b['faithfulness']['strict'] if b['faithfulness']['strict'] is None else round(b['faithfulness']['strict'], 3)} | "
                     f"{b['faithfulness']['lenient'] if b['faithfulness']['lenient'] is None else round(b['faithfulness']['lenient'], 3)} |")
    Path(OUT + ".md").write_text("\n".join(L) + "\n", encoding="utf8")
    print(f"saved {OUT}.json and {OUT}.md")


if __name__ == "__main__":
    raise SystemExit(main())
