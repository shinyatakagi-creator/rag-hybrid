"""python -m eval.robustness_summary  -> eval/results/robustness_summary.{json,md}

Reads saved results only (retrieval_baseline.json, bare_term.json, rrf_weights.json); runs no retrieval and no API call.
For each chunker x mode: Recall@10 and MRR on every slice (exact_term, mixed, conceptual from the baseline; bare_term from the
bare-term diagnostic) and the worst slice per row (lowest Recall@10, ties broken by lower MRR). Weighted-RRF hybrid rows are
a separate sensitivity section (no bare_term slice: that diagnostic was not run with weights).
"""
import json
from pathlib import Path

R = Path("eval/results")
SLICES = ("exact_term", "mixed", "conceptual", "bare_term")
CHUNKERS, MODES = ("fixed", "heading"), ("bm25", "dense", "hybrid")


def slices_for(baseline_row: dict, bare_row: dict | None) -> dict:
    out = {t: {"n": s["n"], "recall@10": s["recall@10"], "mrr": s["mrr"]} for t, s in baseline_row["by_type"].items()}
    if bare_row is not None:
        o = bare_row["overall"]
        out["bare_term"] = {"n": o["n"], "recall@10": o["recall@10"], "mrr": o["mrr"]}
    return out


def worst_slice(slices: dict) -> str:
    return min(slices, key=lambda k: (slices[k]["recall@10"], slices[k]["mrr"]))


def build(baseline: dict, bare: dict, weights: dict) -> dict:
    main = {}
    for c in CHUNKERS:
        for m in MODES:
            name = f"{c}/{m}"
            s = slices_for(baseline["results"][name], bare["results"][name])
            main[name] = {"slices": s, "worst_slice": worst_slice(s)}
    sens = {}
    for name, row in weights["results"].items():
        if "hybrid" in name:
            s = slices_for(row, None)
            sens[name] = {"slices": s, "worst_slice": worst_slice(s)}
    return {"sources": ["eval/results/retrieval_baseline.json", "eval/results/bare_term.json", "eval/results/rrf_weights.json"],
            "worst_slice_rule": "lowest Recall@10, ties broken by lower MRR", "rows": main, "weighted_rrf_sensitivity": sens}


def table(rows: dict, slices: tuple) -> list[str]:
    L = ["| row | " + " | ".join(f"{s} R@10 / MRR (n)" for s in slices) + " | worst slice |", "|---|" + "---|" * (len(slices) + 1)]
    for name, r in rows.items():
        cells = [f"{r['slices'][s]['recall@10']:.3f} / {r['slices'][s]['mrr']:.3f} ({r['slices'][s]['n']})" if s in r["slices"] else "-" for s in slices]
        L.append(f"| {name} | " + " | ".join(cells) + f" | {r['worst_slice']} |")
    return L


def main() -> None:
    load = lambda p: json.loads((R / p).read_text())
    doc = build(load("retrieval_baseline.json"), load("bare_term.json"), load("rrf_weights.json"))
    (R / "robustness_summary.json").write_text(json.dumps(doc, indent=1))
    L = ["# Robustness summary", "", "Built from saved results only (no runs). Each cell is Recall@10 / MRR with the slice size n. "
         "exact_term, mixed and conceptual are the baseline slices of the golden set; bare_term is the diagnostic that queries the exact term alone for the 16 exact_term and mixed questions "
         "(same expected docs). Worst slice = lowest Recall@10, ties broken by lower MRR. n is small (8 / 8 / 10 / 16); read gaps with care.", "",
         "## Baseline rows", "", *table(doc["rows"], SLICES), "",
         "## Weighted-RRF hybrid rows (sensitivity, not tuning; no weight is chosen)", "",
         "Dense weight 1 / 1.5 / 2 with BM25 weight 1; weight 1 is the baseline fusion. No bare_term slice (the diagnostic was not run with weights).", "",
         *table(doc["weighted_rrf_sensitivity"], SLICES[:3]), ""]
    (R / "robustness_summary.md").write_text("\n".join(L), encoding="utf8")
    print("saved eval/results/robustness_summary.{json,md}")


if __name__ == "__main__":
    main()
