"""Checkpoint 4, round 2: a second blind labelling round with an explicit rubric and hidden controls. No API calls.

    python -m eval.checkpoint4_round2 sample    # builds eval/checkpoint4/round2/{labelling_sheet.md, my_labels.csv, key_...json}
    python -m eval.checkpoint4_round2 score     # ONLY after the owner has saved all 30 labels

Sample (seed 2026): 24 verifier-`yes` pairs that were not in round 1 + 6 controls from the verifier mutation set
(eval/verify_mutation.py): 3 known-wrong (M01 swapped citation, M06 changed number, M10 inverted claim; expected label `unsupported`)
and 3 verbatim-correct (C02, C04, C05; expected `supported`), shuffled and numbered M01..M30 in the same format as round 1.
Nothing in the sheet marks a control. The key (kind, source, expected label, verifier verdict) is stored separately.

Pre-registered validity rule: if the owner mislabels more than 1 of the 6 controls (i.e. 2 or more), the round is INVALID for judging the
verifier and is redone; in that case `score` reports the controls and stops. Otherwise `score` reports, in this order: control results,
false-yes rate over the 24 yes pairs (not `supported`; and `unsupported` only) with exact 95% (Clopper-Pearson) intervals, and the
distribution of the owner's labels over the verifier's `yes` (agreement = share labelled `supported`).
"""
import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from eval.checkpoint4 import KEY as KEY1, LABELS_ALLOWED, clopper_pearson, population
from eval.verify_mutation import build
from rag.verify import SNAPSHOT, load_row_chunks

DIR = Path("eval/checkpoint4/round2")
SHEET, LABELS, KEY = DIR / "labelling_sheet.md", DIR / "my_labels.csv", DIR / "key_do_not_open_until_labelled.json"
SEED, N_YES, MAX_BAD_CONTROLS = 2026, 24, 1
WRONG = ("M01", "M06", "M10")     # expected `unsupported`
CORRECT = ("C02", "C04", "C05")   # expected `supported`

RUBRIC = """Rubric: split each sentence into its claims, then judge every claim against the excerpt alone (not against what you know about Kubernetes).

- **supported** = every claim is in the excerpt or directly implied by it (paraphrase counts).
- **partial** = some claims are present in the excerpt and none is contradicted.
- **unsupported** = the excerpt contradicts the sentence, or the sentence's main claim is absent from the excerpt."""


def control_items() -> list[dict]:
    rows = [json.loads(l) for l in open("eval/results/generation_log.jsonl", encoding="utf8")]
    snap = json.loads(Path(SNAPSHOT).read_text())["chunks"]
    found = {m["id"]: (ri, m) for ri, ms in build(rows).items() for m in ms}
    out = []
    for cid in WRONG + CORRECT:
        ri, m = found[cid]
        excerpt = load_row_chunks(rows[ri], snap)[m["citations"][0]]
        out.append({"kind": "control_wrong" if cid in WRONG else "control_correct", "source": cid, "expected": "unsupported" if cid in WRONG else "supported",
                    "sentence": m["sentence"], "excerpt": excerpt})
    return out


def yes_pairs_not_in_round1() -> list[dict]:
    used = {(v["config"], v["qid"], v["sentence_no"], v["citation"]) for v in json.loads(KEY1.read_text())["items"].values()}
    return [p for p in population() if p["verifier"] == "yes" and (p["config"], p["qid"], p["sentence_no"], p["citation"]) not in used]


def draw(yes: list[dict], controls: list[dict], n_yes: int = N_YES, seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    items = [{**p, "kind": "yes_pair"} for p in rng.sample(yes, n_yes)] + list(controls)
    rng.shuffle(items)
    return items


def build_sample() -> int:
    if LABELS.exists() and any(r.get("label", "").strip() for r in csv.DictReader(open(LABELS, encoding="utf8"))):
        print(f"{LABELS} already holds labels; refusing to rebuild over them")
        return 1
    items = draw(yes_pairs_not_in_round1(), control_items())
    DIR.mkdir(parents=True, exist_ok=True)
    L = ["# Checkpoint 4, round 2: label 30 citation pairs", "", RUBRIC, "", f"Write one label per row in `{LABELS}` (columns `id,label,note`; labels `supported`, `partial`, `unsupported`). "
         "Do not open the key file until all 30 labels are saved.", ""]
    for i, p in enumerate(items, 1):
        L += [f"## M{i:02d}", "", f"**Sentence:** {p['sentence']}", "", "**Cited excerpt:**", "", "````text", p["excerpt"], "````", ""]
    SHEET.write_text("\n".join(L), encoding="utf8")
    with open(LABELS, "w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "note"])
        for i in range(1, len(items) + 1):
            w.writerow([f"M{i:02d}", "", ""])
    key = {"seed": SEED, "n_yes": N_YES, "validity_rule": f"invalid if more than {MAX_BAD_CONTROLS} of 6 controls are mislabelled",
           "items": {f"M{i:02d}": ({k: p[k] for k in ("kind", "source", "expected")} if p["kind"] != "yes_pair"
                                   else {k: p[k] for k in ("kind", "config", "qid", "sentence_no", "citation", "verifier")}) for i, p in enumerate(items, 1)}}
    KEY.write_text(json.dumps(key, indent=1))
    print(f"wrote {SHEET}, {LABELS} (empty) and the hidden key: {N_YES} yes pairs + 6 controls, shuffled as M01..M30")
    return 0


def score(items: dict, labels: dict) -> dict:
    if set(labels) != set(items) or any(v not in LABELS_ALLOWED for v in labels.values()):
        raise ValueError("labels must be complete and each one of " + "/".join(LABELS_ALLOWED))
    ctl = {i: it for i, it in items.items() if it["kind"] != "yes_pair"}
    bad = [i for i, it in ctl.items() if labels[i] != it["expected"]]
    res = {"controls": {"n": len(ctl), "mislabelled": len(bad), "valid_round": len(bad) <= MAX_BAD_CONTROLS,
                        "detail": {i: {"source": it["source"], "kind": it["kind"], "expected": it["expected"], "owner": labels[i]} for i, it in sorted(ctl.items())}}}
    if not res["controls"]["valid_round"]:
        res["note"] = f"{len(bad)} of 6 controls mislabelled (more than {MAX_BAD_CONTROLS}): round INVALID for judging the verifier; redo. No verifier statistics reported."
        return res
    yes = [i for i, it in items.items() if it["kind"] == "yes_pair"]
    k = sum(labels[i] != "supported" for i in yes)
    ku = sum(labels[i] == "unsupported" for i in yes)
    res["verifier_yes_pairs"] = {"n": len(yes), "owner_labels": dict(Counter(labels[i] for i in yes)), "agreement_supported": (len(yes) - k) / len(yes),
                                 "false_yes_not_supported": {"k": k, "n": len(yes), "rate": k / len(yes), "ci95_exact": clopper_pearson(k, len(yes))},
                                 "false_yes_unsupported_only": {"k": ku, "n": len(yes), "rate": ku / len(yes), "ci95_exact": clopper_pearson(ku, len(yes))}}
    return res


def run_score() -> int:
    labels = {r["id"]: r["label"].strip().lower() for r in csv.DictReader(open(LABELS, encoding="utf8"))}
    if any(not v for v in labels.values()):
        print(f"{sum(not v for v in labels.values())} labels are still empty in {LABELS}: nothing computed")
        return 1
    res = score(json.loads(KEY.read_text())["items"], labels)
    (DIR / "agreement.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "score"])
    a = ap.parse_args(argv)
    return build_sample() if a.cmd == "sample" else run_score()


if __name__ == "__main__":
    raise SystemExit(main())
