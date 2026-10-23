"""python -m eval.verify_mutation [--dry-run]

Does the verifier notice wrong pairs? Ten deliberate mutations of the saved answers in generation_log.jsonl:
  A) citation swapped to an unrelated excerpt from the same context (sentence unchanged)   x5
  B) sentence altered (changed number, wrong component, inverted claim) keeping its real citation   x5
Expected verdict for all ten is "no" (a "partial" is a soft catch, a "yes" is a miss). The unmodified originals are the
controls: they are verified separately by `python -m rag.verify`. Mutations are grouped into one batched call per source answer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from ingest.embed_cache import SpendGuard
from rag.verify import SNAPSHOT, load_row_chunks, verify_answer

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
    ("C01", "control_model", 0, 3, None, None),
    ("C02", "control_authored", 0, None, "Process IDs (PIDs) are a fundamental resource on nodes.", [2]),
    ("C03", "control_authored", 0, None, "On certain Linux installations, the operating system sets the PIDs limit to a low default, such as 32768.", [2]),
    ("C04", "control_authored", 1, None, "Each incoming request is assigned to a single priority level.", [2]),
    ("C05", "control_authored", 1, None, "APF classifies and isolates requests in a more fine-grained way.", [1]),
]


def build(rows: list[dict]) -> dict[int, list[dict]]:
    """Group mutated and control sentences by source row (shuffled deterministically by id, so position is no cue).
    Each item keeps the original for the report."""
    by_row: dict[int, list[dict]] = {}
    for cid, kind, ri, si, text, cites in CONTROLS:
        orig = rows[ri]["answer"]["sentences"][si] if si is not None else {"sentence": text, "citations": cites}
        by_row.setdefault(ri, []).append({"id": cid, "kind": kind, "orig_sentence": orig["sentence"], "orig_citations": orig["citations"],
                                          "sentence": orig["sentence"], "citations": list(orig["citations"])})
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


def main(argv=None) -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="eval/results/generation_log.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    import anthropic
    model = os.environ["VERIFIER_MODEL"]
    guard = SpendGuard(float(os.environ.get("MAX_SPEND_USD", "5")))
    rows = [json.loads(l) for l in open(a.log, encoding="utf8")]
    snap = json.loads(Path(SNAPSHOT).read_text())["chunks"]
    client = None if a.dry_run else anthropic.Anthropic()
    results, total = [], 0.0
    for ri, items in build(rows).items():
        sentences = [{"sentence": m["sentence"], "citations": m["citations"]} for m in items]
        chunks = load_row_chunks(rows[ri], snap)
        confirm = lambda est: input(f"Verify {len(items)} mutated pairs from row {ri}: ~{est['input_tokens_est']} input tokens "
                                    f"(est. ${est['input_cost_est']:.5f}), worst case ${est['worst_case_cost']:.5f}. Proceed? [y/N] ").strip().lower() == "y"
        r = verify_answer(client, guard, model, sentences, chunks, dry_run=a.dry_run, confirm=confirm)
        if a.dry_run:
            total += r["estimate"]["input_cost_est"]
            print(f"row {ri}: {r['pairs']} mutated pairs, ~{r['estimate']['input_tokens_est']} input tokens = ${r['estimate']['input_cost_est']:.5f}; worst case ${r['estimate']['worst_case_cost']:.5f}")
            continue
        for m, j in zip(items, r["judgements"]):
            results.append({**m, "verdict": j["verdict"], "reason": j["reason"], "source_row": ri, "cost_share": r["cost_usd"] / len(items)})
    if a.dry_run:
        print(f"\nDRY RUN total (input only): ${total:.5f}. No API call made.")
        return
    print(f"{'id':4} {'kind':16} {'verdict':8} reason")
    for x in sorted(results, key=lambda x: x["id"]):
        print(f"{x['id']:4} {x['kind']:16} {x['verdict'].upper():8} {x['reason']}")
    wrong = [x for x in results if x["kind"] in ("swap", "text")]
    ctrl = [x for x in results if x["kind"].startswith("control")]
    tally = lambda xs: {v: sum(1 for x in xs if x["verdict"] == v) for v in ("no", "partial", "yes")}
    summary = {"wrong_pairs": {"n": len(wrong), **tally(wrong)}, "swap": tally([x for x in wrong if x["kind"] == "swap"]),
               "text": tally([x for x in wrong if x["kind"] == "text"]), "controls": {"n": len(ctrl), **tally(ctrl)}}
    w, c = summary["wrong_pairs"], summary["controls"]
    print(f"\nWRONG pairs (n={w['n']}): no={w['no']} partial={w['partial']} yes(missed)={w['yes']}  -> hard catch rate {w['no']}/{w['n']}, catch incl. partial {w['no'] + w['partial']}/{w['n']}")
    print(f"   swapped citation: {summary['swap']}   altered sentence: {summary['text']}")
    print(f"CONTROLS (n={c['n']}): yes={c['yes']} partial={c['partial']} no={c['no']}  -> false-alarm rate {c['partial'] + c['no']}/{c['n']} (hard 'no': {c['no']}/{c['n']})")
    out = {"model": model, "n": len(results), "summary": summary, "results": results, "spend_usd": guard.spent}
    Path("eval/results").mkdir(parents=True, exist_ok=True)
    Path("eval/results/verify_mutation.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"spend ${guard.spent:.6f}; saved eval/results/verify_mutation.json")


if __name__ == "__main__":
    main()
