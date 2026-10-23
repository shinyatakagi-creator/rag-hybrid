"""python -m eval.answer_eval_review  -> eval/results/answer_eval_review.md

Review report built from the saved answer_eval logs only (no API call): outcome vs context coverage, the full answers to the
unanswerable questions, usage and cost, and every (sentence, excerpt) pair the verifier did not mark `yes`, for the owner's review.
"""
import json
from collections import defaultdict
from pathlib import Path

from eval.answer_eval import CONFIGS, GEN_LOG, VER_LOG, best_verdict_per_sentence
from eval.retrieval_eval import load_golden


def main() -> None:
    gold = {q["id"]: q for q in load_golden("eval/golden.jsonl")}
    gens = {(r["config"], r["qid"]): r for r in map(json.loads, Path(GEN_LOG).read_text(encoding="utf8").splitlines())}
    vers = {(r["config"], r["qid"]): r for r in map(json.loads, Path(VER_LOG).read_text(encoding="utf8").splitlines())}
    L = ["# Answer eval: review report", "", "Built from `answer_eval_generation.jsonl` and `answer_eval_verification.jsonl` only. Verdicts come from the Haiku verifier (claims-v2); "
         "they are not hand-checked yet (checkpoint 4).", ""]

    L += ["## Outcome vs context coverage (answerable questions, n = 26)", "",
          "Coverage = at least one expected doc is among the 8 context chunks. A refusal with coverage = no is a retrieval miss; a refusal with coverage = yes is a generation decision.", "",
          "| config | covered & answered | covered & refused | not covered & answered | not covered & refused |", "|---|---|---|---|---|"]
    refused_rows = []
    for c in CONFIGS:
        t = defaultdict(int)
        for qid, q in gold.items():
            if not q["answerable"]:
                continue
            g = gens[(c, qid)]
            cov = bool({ch["doc_id"] for ch in g["chunks"]} & set(q["expected_doc_ids"]))
            ref = not g["answer"]["answerable"]
            t[(cov, ref)] += 1
            if ref:
                refused_rows.append((c, qid, cov))
        L.append(f"| {c} | {t[(True, False)]} | {t[(True, True)]} | {t[(False, False)]} | {t[(False, True)]} |")
    L += ["", "False refusals: " + "; ".join(f"{c} {qid} ({'expected doc in context' if cov else 'expected doc NOT in context'})" for c, qid, cov in refused_rows), ""]

    L += ["## Unanswerable questions: full answers", ""]
    for qid in [i for i, q in gold.items() if not q["answerable"]]:
        for c in CONFIGS:
            g = gens[(c, qid)]
            a = g["answer"]
            L += [f"### {qid} / {c}: {gold[qid]['question']}", "", f"answerable={a['answerable']}; context: " + ", ".join(sorted({ch['doc_id'].split('/')[-1] for ch in g['chunks']})), ""]
            L += [f"> {s['sentence']}  (citations {s['citations']})" for s in a["sentences"]] + [""]

    L += ["## Usage and cost (from the `usage` fields)", "", "| step | calls | input tokens | output tokens | cost | per call |", "|---|---|---|---|---|---|"]
    for name, rows in (("generation", list(gens.values())), ("verification", list(vers.values()))):
        rows = [r for r in rows if "usage" in r]
        tin, tout, cost = sum(r["usage"]["input_tokens"] for r in rows), sum(r["usage"]["output_tokens"] for r in rows), sum(r["cost_usd"] for r in rows)
        L.append(f"| {name} | {len(rows)} | {tin:,} | {tout:,} | ${cost:.4f} | {tin / len(rows):,.0f} in / {tout / len(rows):,.0f} out / ${cost / len(rows):.4f} |")
    allc = sum(r["cost_usd"] for r in gens.values()) + sum(r.get("cost_usd", 0) for r in vers.values())
    L += ["", f"Total ${allc:.4f} for {len(gens)} questions x configs (${allc / len(gens):.4f} per question-config; {allc / 30:.4f} per question across both configs). "
          "Refusals cost less (about 70 output tokens) than answers.", ""]
    L.append("The run printed a total spend of $0.7295 (spend guard); the logs sum to less because the one failed verification call (hybrid e007) did not record its usage in this run (fixed in rag/verify.py afterwards, see NOTES.md).")
    L.append("")
    for c in CONFIGS:
        rs = [r for k, r in gens.items() if k[0] == c]
        L.append(f"- {c}: generation ${sum(r['cost_usd'] for r in rs):.4f}, mean latency {sum(r['latency_s'] for r in rs) / len(rs):.1f}s")
    L.append("")

    L += ["## Verifier output that is not `yes`", ""]
    errs = [(k, v["error"]) for k, v in vers.items() if "error" in v]
    L += [f"Verification errors (no verdicts, excluded from faithfulness): " + ("; ".join(f"{c} {q}: {e}" for (c, q), e in errs) if errs else "none"), ""]
    n_pairs = n_bad = 0
    out = []
    for (c, qid), v in sorted(vers.items()):
        if "judgements" not in v:
            continue
        g = gens[(c, qid)]
        sents = g["answer"]["sentences"]
        excerpt = {ch["n"]: ch for ch in g["chunks"]}
        best = best_verdict_per_sentence(v["judgements"])
        for j in v["judgements"]:
            n_pairs += 1
            if j["verdict"] == "yes":
                continue
            n_bad += 1
            ch = excerpt[j["citation"]]
            claims = ", ".join(f"{x['status']}: {x['claim']}" for x in j["claims"])
            out += [f"### {c} {qid} sentence {j['sentence']} vs excerpt [{j['citation']}]: **{j['verdict'].upper()}** (sentence's best verdict: {best[j['sentence']]})", "",
                    f"Sentence: {sents[j['sentence'] - 1]['sentence']}", "",
                    f"Verifier reason: {j['reason']}", "", f"Claims: {claims}", "",
                    f"Excerpt [{j['citation']}] ({ch['doc_id']} | {ch['heading_path']}; expected doc: {ch['doc_id'] in gold[qid]['expected_doc_ids']}):", "", "````text", ch["content"], "````", ""]
    L += [f"{n_bad} of {n_pairs} cited pairs were not `yes`.", ""] + out
    Path("eval/results/answer_eval_review.md").write_text("\n".join(L), encoding="utf8")
    print(f"saved eval/results/answer_eval_review.md ({n_bad} of {n_pairs} pairs not yes)")


if __name__ == "__main__":
    main()
