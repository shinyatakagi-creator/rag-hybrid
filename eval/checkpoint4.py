"""Checkpoint 4: hand-label verifier judgements, then measure agreement. Two steps, deliberately separate.

    python -m eval.checkpoint4 sample            # builds the blind sheet + empty labels file + hidden key; no API call, no labels used
    python -m eval.checkpoint4 score             # ONLY after the owner has filled and saved eval/checkpoint4/my_labels.csv

Sample (seeded): every cited (sentence, excerpt) pair the Haiku verifier did NOT mark `yes` (11) + 19 random `yes` pairs,
shuffled and numbered L01..L30. The labelling sheet shows only the sentence and the cited excerpt text (exactly what the
verifier saw): no verdict, reason, claims, config, question id or question type, and no source page or heading. The key that
maps each number back to its pair and verifier verdict is stored separately.

Labels: supported | partial | unsupported, judged from that excerpt alone (not from outside knowledge). Verifier `yes`/`partial`/`no`
are compared as supported/partial/unsupported.

Score (computed only from the saved labels): exact agreement, the 3x3 confusion matrix, and the false-yes rate = share of the
verifier's `yes` pairs in the sample that the owner did not label `supported` (and, separately, labelled `unsupported`) with an
exact (Clopper-Pearson) 95% interval. The sample over-represents non-yes pairs, so overall agreement is also reported per stratum
and reweighted to the full population of cited pairs.
"""
import argparse
import csv
import json
import math
import random
from collections import Counter
from pathlib import Path

from eval.answer_eval import GEN_LOG, VER_LOG, read_log

DIR = Path("eval/checkpoint4")
SHEET, LABELS, KEY = DIR / "labelling_sheet.md", DIR / "my_labels.csv", DIR / "key_do_not_open_until_labelled.json"
SEED, N_YES = 30, 19
LABELS_ALLOWED = ("supported", "partial", "unsupported")
MAP = {"yes": "supported", "partial": "partial", "no": "unsupported"}


def population() -> list[dict]:
    """Every verified (sentence, citation) pair from the latest verification row per answer, in a fixed order."""
    gens = read_log(GEN_LOG, lambda r: (r["config"], r["qid"]))
    vers = read_log(VER_LOG, lambda r: (r["config"], r["qid"]))
    pairs = []
    for key in sorted(vers):
        v = vers[key]
        if "judgements" not in v:
            continue
        g = gens[key]
        excerpt = {c["n"]: c["content"] for c in g["chunks"]}
        for j in sorted(v["judgements"], key=lambda j: (j["sentence"], j["citation"])):
            pairs.append({"config": key[0], "qid": key[1], "sentence_no": j["sentence"], "citation": j["citation"], "verifier": j["verdict"],
                          "sentence": g["answer"]["sentences"][j["sentence"] - 1]["sentence"], "excerpt": excerpt[j["citation"]]})
    return pairs


def draw(pairs: list[dict], n_yes: int = N_YES, seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    non_yes = [p for p in pairs if p["verifier"] != "yes"]
    yes = [p for p in pairs if p["verifier"] == "yes"]
    sample = non_yes + rng.sample(yes, n_yes)
    rng.shuffle(sample)
    return sample


def build() -> int:
    pairs = population()
    sample = draw(pairs)
    DIR.mkdir(parents=True, exist_ok=True)
    if LABELS.exists() and any(r.get("label", "").strip() for r in csv.DictReader(open(LABELS, encoding="utf8"))):
        print(f"{LABELS} already holds labels; refusing to rebuild the sample over them")
        return 1
    L = ["# Checkpoint 4: label 30 citation pairs", "",
         "For each item, read the sentence and the excerpt it cites, and decide from the excerpt ALONE (not from what you know about Kubernetes) whether the excerpt supports the sentence:", "",
         "- **supported**: the excerpt states the sentence's claims or directly implies them (paraphrase and equivalent numbers count);", "- **partial**: some of the claims are supported, others are not (or go beyond the excerpt);",
         "- **unsupported**: the excerpt does not support the sentence, or contradicts it.", "", f"Write one label per row in `{LABELS}` (columns `id,label,note`). Do not open the key file until you have saved all 30 labels.", ""]
    for i, p in enumerate(sample, 1):
        L += [f"## L{i:02d}", "", f"**Sentence:** {p['sentence']}", "", "**Cited excerpt:**", "", "````text", p["excerpt"], "````", ""]
    SHEET.write_text("\n".join(L), encoding="utf8")
    with open(LABELS, "w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "note"])
        for i in range(1, len(sample) + 1):
            w.writerow([f"L{i:02d}", "", ""])
    key = {"seed": SEED, "n_yes_sampled": N_YES, "population": {"pairs": len(pairs), "yes": sum(p["verifier"] == "yes" for p in pairs), "not_yes": sum(p["verifier"] != "yes" for p in pairs)},
           "items": {f"L{i:02d}": {k: p[k] for k in ("config", "qid", "sentence_no", "citation", "verifier")} for i, p in enumerate(sample, 1)}}
    KEY.write_text(json.dumps(key, indent=1))
    print(f"wrote {SHEET} ({len(sample)} items: {sum(p['verifier'] != 'yes' for p in sample)} non-yes + {N_YES} yes, shuffled), {LABELS} (empty) and the hidden key")
    return 0


# -- scoring (pure functions, unit-tested; run only on saved labels) ------------------------------------------------------------
def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided (1 - alpha) interval for a binomial proportion, by bisection on the binomial CDF."""
    def solve(f, lo=0.0, hi=1.0):
        for _ in range(100):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(lambda p: 1 - _binom_cdf(k - 1, n, p) < alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: _binom_cdf(k, n, p) > alpha / 2)
    return lower, upper


def score(items: dict, labels: dict, population: dict) -> dict:
    """items: id -> {verifier,...}; labels: id -> supported|partial|unsupported; population: {'yes': n, 'not_yes': n}."""
    if set(labels) != set(items) or any(v not in LABELS_ALLOWED for v in labels.values()):
        raise ValueError("labels must be complete and each one of " + "/".join(LABELS_ALLOWED))
    conf = {h: {v: 0 for v in LABELS_ALLOWED} for h in LABELS_ALLOWED}  # conf[human][verifier]
    for i, it in items.items():
        conf[labels[i]][MAP[it["verifier"]]] += 1
    agree = sum(conf[l][l] for l in LABELS_ALLOWED)
    n = len(items)
    yes_ids = [i for i, it in items.items() if it["verifier"] == "yes"]
    non_ids = [i for i in items if i not in yes_ids]
    fy = sum(labels[i] != "supported" for i in yes_ids)
    fy_strict = sum(labels[i] == "unsupported" for i in yes_ids)
    agree_yes = sum(MAP[items[i]["verifier"]] == labels[i] for i in yes_ids)
    agree_non = sum(MAP[items[i]["verifier"]] == labels[i] for i in non_ids)
    pop_yes, pop_non = population["yes"], population["not_yes"]
    weighted = (agree_yes / len(yes_ids) * pop_yes + (agree_non / len(non_ids) * pop_non if non_ids else 0)) / (pop_yes + pop_non) if yes_ids else None
    return {"n": n, "agreement": agree / n, "agreement_count": agree, "confusion_human_rows_verifier_columns": conf,
            "yes_stratum": {"n": len(yes_ids), "agree": agree_yes}, "not_yes_stratum": {"n": len(non_ids), "agree": agree_non},
            "population_weighted_agreement": weighted,
            "false_yes_rate": {"k": fy, "n": len(yes_ids), "rate": fy / len(yes_ids) if yes_ids else None, "ci95_exact": clopper_pearson(fy, len(yes_ids)) if yes_ids else None},
            "false_yes_rate_unsupported_only": {"k": fy_strict, "n": len(yes_ids), "rate": fy_strict / len(yes_ids) if yes_ids else None,
                                                "ci95_exact": clopper_pearson(fy_strict, len(yes_ids)) if yes_ids else None}}


def run_score() -> int:
    rows = list(csv.DictReader(open(LABELS, encoding="utf8")))
    labels = {r["id"]: r["label"].strip().lower() for r in rows}
    if any(not v for v in labels.values()):
        print(f"{sum(not v for v in labels.values())} labels are still empty in {LABELS}: nothing computed")
        return 1
    key = json.loads(KEY.read_text())
    res = score(key["items"], labels, key["population"])
    out = DIR / "agreement.json"
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sample", "score"])
    a = ap.parse_args(argv)
    return build() if a.cmd == "sample" else run_score()


if __name__ == "__main__":
    raise SystemExit(main())
