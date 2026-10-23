"""python -m eval.verify_mutation [--dry-run] [--model ID] [--tag NAME]
python -m eval.verify_mutation --compare A.json B.json

A DEV SET for the verifier rubric, not an accuracy measurement (that comes from the owner's hand labels at checkpoint 4).
25 pairs built from the saved answers in generation_log.jsonl, grouped into one batched call per source answer:
  wrong, expected "no":   10  swapped citation x5 (sentence unchanged) and altered sentence x5 (number, component, inversion)
  verbatim controls:       5  sentences copied from the cited excerpt (expected "yes")
  paraphrased controls:   10  sentences I wrote from the cited excerpt: meaning kept, wording changed, numbers in an equivalent
                              form (expected "yes"); reviewed by eye only, they are not machine-checked to be faithful
Reported separately: catch rate on the wrong pairs, false-alarm rate on verbatim and on paraphrased controls.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from ingest.embed_cache import SpendGuard
from rag.verify import RUBRIC, SNAPSHOT, load_row_chunks, verify_answer

# (id, kind, source row, sentence index, new citation or None, (old, new) text replacement or None)
MUTATIONS = [
    ("M01", "swap", 0, 0, 6, None),   # PID limit sentence -> Pod Lifecycle "Termination of Pods"
    ("M02", "swap", 0, 2, 3, None),   # 262144 PIDs example -> HPA "Stop generating load"
    ("M03", "swap", 0, 4, 8, None),   # reserve PIDs for node overhead -> Resource Quotas "Quota and Cluster Capacity"
    ("M04", "swap", 1, 1, 5, None),   # APF disabled: limited by two flags -> kube-apiserver traces
    ("M05", "swap", 1, 4, 3, None),   # watch requests exempt -> EventRateLimit admission controller
    ("M06", "text", 0, 2, None, ("262144 PIDs", "524288 PIDs")),                        # changed number
    ("M07", "text", 0, 1, None, ("a setting on the kubelet", "a setting on the kube-scheduler")),  # wrong component
    ("M08", "text", 0, 5, None, ("does not ensure that all Pods scheduled onto a host are unable",
                                 "ensures that all Pods scheduled onto a host are unable")),       # inverted claim
    ("M09", "text", 1, 2, None, ("are summed and the sum is divided", "are multiplied and the product is divided")),  # changed operation
    ("M10", "text", 1, 3, None, ("are not subject to this limit", "are always subject to this limit")),  # inverted claim
]


# Controls: pairs that ARE supported. (id, kind, source row, saved sentence index or None, authored sentence or None, citations or None)
# C01 is a saved model sentence the excerpt supports; C02-C05 are sentences I authored, each verbatim from the cited excerpt
# (checked by a test), so a "no" or "partial" on them is a false alarm.
CONTROLS = [
    ("C01", "control_verbatim", 0, 3, None, None),
    ("C02", "control_verbatim", 0, None, "Process IDs (PIDs) are a fundamental resource on nodes.", [2]),
    ("C03", "control_verbatim", 0, None, "On certain Linux installations, the operating system sets the PIDs limit to a low default, such as 32768.", [2]),
    ("C04", "control_verbatim", 1, None, "Each incoming request is assigned to a single priority level.", [2]),
    ("C05", "control_verbatim", 1, None, "APF classifies and isolates requests in a more fine-grained way.", [1]),
]

# Paraphrased controls: (id, source row, sentence, citations). Meaning preserved against the cited excerpt, wording changed,
# numbers in an equivalent form (262,144 / 1,000 / 32,768). Row 0 chunk [2] is the PID-limits page, [4] the multi-tenancy
# node-isolation section; row 1 chunks [1], [2] are the API Priority and Fairness page.
PARAPHRASES = [
    ("P01", 0, "Kubernetes lets you cap how many PIDs a single Pod may consume.", [2]),
    ("P02", 0, "Administrators can set aside part of a node's allocatable PIDs for the operating system and system daemons instead of for Pods.", [2]),
    ("P03", 0, "The task limit can easily be reached before any other resource limit is hit, and that can leave the host machine unstable.", [2]),
    ("P04", 0, "On a node whose OS allows at most 262,144 PIDs and which is expected to host fewer than 250 Pods, each Pod can be given a budget of 1,000 PIDs.", [2]),
    ("P05", 0, "Some Linux installations ship with a low default PIDs limit, for example 32,768, so it may be worth raising the value of pid_max.", [2]),
    ("P06", 0, "Dedicating particular nodes to a single tenant's pods lessens the noisy tenant problem, since all pods on such a node belong to one tenant.", [4]),
    ("P07", 0, "Node isolation slightly lowers the risk of information disclosure, because an attacker who escapes from a container can only reach the containers and volumes on that node.", [4]),
    ("P08", 1, "APF adds a small amount of queuing so that very brief bursts of traffic do not cause requests to be rejected.", [1]),
    ("P09", 1, "The two max-inflight flags alone cannot guarantee that the most important requests get served when traffic is heavy.", [1]),
    ("P10", 1, "A Pod that floods the API server with requests cannot stop leader election or the built-in controllers from working, because the default configuration gives those requests separate priority levels.", [2]),
]


def build(rows: list[dict]) -> dict[int, list[dict]]:
    """Group mutated and control sentences by source row (shuffled deterministically by id, so position is no cue).
    Each item keeps the original for the report."""
    by_row: dict[int, list[dict]] = {}
    for cid, kind, ri, si, text, cites in CONTROLS:
        orig = rows[ri]["answer"]["sentences"][si] if si is not None else {"sentence": text, "citations": cites}
        by_row.setdefault(ri, []).append({"id": cid, "kind": kind, "orig_sentence": orig["sentence"], "orig_citations": orig["citations"],
                                          "sentence": orig["sentence"], "citations": list(orig["citations"])})
    for pid, ri, text, cites in PARAPHRASES:
        by_row.setdefault(ri, []).append({"id": pid, "kind": "control_paraphrase", "orig_sentence": text, "orig_citations": cites,
                                          "sentence": text, "citations": list(cites)})
    for mid, kind, ri, si, new_cite, repl in MUTATIONS:
        orig = rows[ri]["answer"]["sentences"][si]
        sentence, cites = orig["sentence"], list(orig["citations"])
        if kind == "swap":
            if new_cite in cites or not 1 <= new_cite <= len(rows[ri]["chunks"]):
                raise ValueError(f"{mid}: swap target {new_cite} must be another chunk of that answer")
            cites = [new_cite]
        else:
            old, new = repl
            if old not in sentence:
                raise ValueError(f"{mid}: {old!r} not found in the saved sentence")
            sentence = sentence.replace(old, new)
        by_row.setdefault(ri, []).append({"id": mid, "kind": kind, "orig_sentence": orig["sentence"], "orig_citations": orig["citations"],
                                          "sentence": sentence, "citations": cites})
    return {ri: sorted(items, key=lambda m: hashlib.sha1(m["id"].encode()).hexdigest()) for ri, items in by_row.items()}


def summarize_results(results: list[dict]) -> dict:
    tally = lambda xs: {v: sum(1 for x in xs if x["verdict"] == v) for v in ("no", "partial", "yes")}
    cat = lambda *kinds: [x for x in results if x["kind"] in kinds]
    wrong, verb, para = cat("swap", "text"), cat("control_verbatim"), cat("control_paraphrase")
    return {
        "wrong_pairs": {"n": len(wrong), **tally(wrong)}, "swap": tally(cat("swap")), "text": tally(cat("text")),
        "controls_verbatim": {"n": len(verb), **tally(verb)}, "controls_paraphrase": {"n": len(para), **tally(para)},
    }


def print_summary(s: dict) -> None:
    w, v, p = s["wrong_pairs"], s["controls_verbatim"], s["controls_paraphrase"]
    print(f"\nWRONG pairs (n={w['n']}): no={w['no']} partial={w['partial']} yes(missed)={w['yes']}  -> catch rate (not 'yes') {w['no'] + w['partial']}/{w['n']}, hard 'no' {w['no']}/{w['n']}")
    print(f"   swapped citation: {s['swap']}   altered sentence: {s['text']}")
    print(f"VERBATIM controls (n={v['n']}): yes={v['yes']} partial={v['partial']} no={v['no']}  -> false-alarm rate (not 'yes') {v['partial'] + v['no']}/{v['n']}, hard 'no' {v['no']}/{v['n']}")
    print(f"PARAPHRASED controls (n={p['n']}): yes={p['yes']} partial={p['partial']} no={p['no']}  -> false-alarm rate (not 'yes') {p['partial'] + p['no']}/{p['n']}, hard 'no' {p['no']}/{p['n']}")


def compare(path_a: str, path_b: str) -> None:
    a, b = (json.loads(Path(p).read_text()) for p in (path_a, path_b))
    ra, rb = {x["id"]: x for x in a["results"]}, {x["id"]: x for x in b["results"]}
    print(f"{'id':4} {'kind':18} {a['model']:>18} {b['model']:>18}  agree")
    agree = 0
    for i in sorted(ra):
        same = ra[i]["verdict"] == rb[i]["verdict"]
        agree += same
        print(f"{i:4} {ra[i]['kind']:18} {ra[i]['verdict'].upper():>18} {rb[i]['verdict'].upper():>18}  {'' if same else '<-- differ'}")
    n = len(ra)
    print(f"\nexact agreement {agree}/{n} = {agree / n:.0%}")
    tally = lambda rs: {v: sum(1 for x in rs if x["verdict"] == v) for v in ("no", "partial", "yes")}
    for kinds, name in ((("swap", "text"), "wrong pairs"), (("control_verbatim",), "verbatim controls"), (("control_paraphrase",), "paraphrased controls")):
        ids = [i for i in ra if ra[i]["kind"] in kinds]
        print(f"   {name:20} agree {sum(ra[i]['verdict'] == rb[i]['verdict'] for i in ids):2d}/{len(ids):2d}   "
              f"{a['model']}: {tally([ra[i] for i in ids])}   {b['model']}: {tally([rb[i] for i in ids])}")


def main(argv=None) -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="eval/results/generation_log.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=None, help="verifier model (default VERIFIER_MODEL)")
    ap.add_argument("--tag", default=None, help="output file suffix (default: the model id)")
    ap.add_argument("--compare", nargs=2, metavar=("A.json", "B.json"))
    a = ap.parse_args(argv)
    if a.compare:
        return compare(*a.compare)
    import anthropic
    model = a.model or os.environ["VERIFIER_MODEL"]
    guard = SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5")))
    rows = [json.loads(l) for l in open(a.log, encoding="utf8")]
    snap = json.loads(Path(SNAPSHOT).read_text())["chunks"]
    client = None if a.dry_run else anthropic.Anthropic()
    results, total = [], 0.0
    for ri, items in build(rows).items():
        sentences = [{"sentence": m["sentence"], "citations": m["citations"]} for m in items]
        chunks = load_row_chunks(rows[ri], snap)
        confirm = lambda est: input(f"Verify {len(items)} pairs from row {ri} with {model}: ~{est['input_tokens_est']} input tokens "
                                    f"(est. ${est['input_cost_est']:.5f}), worst case ${est['worst_case_cost']:.5f}. Proceed? [y/N] ").strip().lower() == "y"
        r = verify_answer(client, guard, model, sentences, chunks, dry_run=a.dry_run, confirm=confirm)
        if a.dry_run:
            total += r["estimate"]["input_cost_est"]
            print(f"row {ri}: {r['pairs']} pairs, ~{r['estimate']['input_tokens_est']} input tokens = ${r['estimate']['input_cost_est']:.5f}; worst case ${r['estimate']['worst_case_cost']:.5f}")
            continue
        for m, j in zip(items, r["judgements"]):
            results.append({**m, "verdict": j["verdict"], "claims": j["claims"], "reason": j["reason"], "source_row": ri,
                            "cost_share": r["cost_usd"] / len(items)})
    if a.dry_run:
        print(f"\nDRY RUN total (input only): ${total:.5f}. No API call made.")
        return
    print(f"{'id':4} {'kind':19} {'verdict':8} {'claims':8} reason")
    marks = lambda cl: "".join({"supported": "S", "unsupported": "U", "contradicted": "C"}[c["status"]] for c in cl)
    for x in sorted(results, key=lambda x: x["id"]):
        print(f"{x['id']:4} {x['kind']:19} {x['verdict'].upper():8} {marks(x['claims']):8} {x['reason']}")
    summary = summarize_results(results)
    print_summary(summary)
    out = {"model": model, "rubric": RUBRIC, "n": len(results), "summary": summary, "results": results, "spend_usd": guard.spent}
    path = Path(f"eval/results/verify_mutation_{a.tag or model}.json")
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"spend ${guard.spent:.6f}; saved {path}")


if __name__ == "__main__":
    main()
