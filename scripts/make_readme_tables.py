"""Generate README.md, docs/numbers_manifest.json and docs/NUMBERS_AUDIT.md from the saved results.

Every number that ends up in README.md goes through one helper that records its value and source:
  V()  a lookup in eval/results/*.json         (kind "result")
  X()  a value computed here from those files   (kind "computed")
  D()  a figure or text taken from a prose doc   (kind "doc")
  T()  a typed constant with a stated reason     (kind "typed")
The helpers wrap the text in private-use marker characters; finalize() strips them and records the
exact character span of each value in the final README. tests/test_readme_numbers.py then requires
that every digit in README.md lies inside a recorded span whose text still matches, so a hand-typed
or hand-edited digit fails. No API calls, no Elasticsearch.

    python scripts/make_readme_tables.py
"""
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "eval" / "results"
S, M, E = "", "", ""
_cache, ENTRIES = {}, []


def J(name):
    if name not in _cache:
        _cache[name] = json.loads((RES / name).read_text())
    return _cache[name]


def mark(text, kind, source, key="", label=""):
    ENTRIES.append({"kind": kind, "source": source, "key": key, "label": label})
    return f"{S}{len(ENTRIES) - 1}{M}{text}{E}"


def dig(file, path):
    o = J(file)
    for p in path:
        o = o[p]
    return o


def V(file, path, fmt="{:.3f}", label=""):
    return mark(fmt.format(dig(file, path)), "result", f"eval/results/{file}", " > ".join(map(str, path)), label)


def CI(file, path, key="recall@10_ci95"):
    lo, hi = dig(file, path)[key]
    return mark(f"{lo:.3f}-{hi:.3f}", "result", f"eval/results/{file}", " > ".join(map(str, path)) + f" > {key}", "95% CI")


def X(text, source, key, label=""):
    return mark(text, "computed", source, key, label)


def D(text, source, label):
    return mark(text, "doc", source, "", label)


def T(text, label, source):
    return mark(text, "typed", source, "", label)


def text_between(path, start, pattern):
    t = (ROOT / path).read_text()
    return re.findall(pattern, t[t.index(start):].split("\n## ", 1)[0], flags=re.M)


ROWS = ["fixed/bm25", "fixed/dense", "fixed/hybrid", "heading/bm25", "heading/dense", "heading/hybrid"]
RB, AE, RS = "retrieval_baseline.json", "answer_eval.json", "robustness_summary.json"
TYPES = ["exact_term", "mixed", "conceptual"]


def sizes():
    z = {t: V(RB, ("meta", "n_by_type", t), "{}") for t in TYPES}
    z["bare"] = V("bare_term.json", ("results", "heading/bm25", "overall", "n"), "{}")
    return z


def exact_bounds(n, rate):
    """Clopper-Pearson 95% bounds when every question is a hit (rate 1) or a miss (rate 0); else None.
    The closed forms are the two edge cases of the beta-quantile definition: (0.025)**(1/n)."""
    if rate == 1.0:
        return 0.025 ** (1 / n), 1.0
    if rate == 0.0:
        return 0.0, 1 - 0.025 ** (1 / n)
    return None


def ci_cell(file, path):
    """Bootstrap interval, plus the exact interval when the bootstrap one collapses to a point."""
    o = dig(file, path)
    boot = CI(file, path)
    b = exact_bounds(o["n"], o["recall@10"])
    if b is None:
        return boot
    ex = X(f"{b[0]:.3f}-{b[1]:.3f}", "computed here", f"Clopper-Pearson, n={o['n']}, every question {'a hit' if o['recall@10'] == 1.0 else 'a miss'}", "exact 95% interval")
    return f"{boot}; exact {ex}"


# ---------------------------------------------------------------- tables
def robustness_table():
    z = sizes()
    out = [f"| row | exact_term (n={z['exact_term']}) | mixed (n={z['mixed']}) | conceptual (n={z['conceptual']}) | bare_term (n={z['bare']}) | worst slice |", "|---|---|---|---|---|---|"]
    for r in ROWS:
        cells = []
        for s in TYPES + ["bare_term"]:
            p = ("rows", r, "slices", s)
            cells.append(f"{V(RS, p + ('recall@10',))} / {V(RS, p + ('mrr',))}")
        out.append(f"| {r} | " + " | ".join(cells) + f" | {J(RS)['rows'][r]['worst_slice']} |")
    return "\n".join(out)


def bare_table():
    out = ["| row | n | Recall@10 (95% CI) | MRR (95% CI) |", "|---|---|---|---|"]
    for r in ROWS:
        p = ("results", r, "overall")
        out.append(f"| {r} | {V('bare_term.json', p + ('n',), '{}')} | {V('bare_term.json', p + ('recall@10',))} "
                   f"({ci_cell('bare_term.json', p)}) | {V('bare_term.json', p + ('mrr',))} ({CI('bare_term.json', p, 'mrr_ci95')}) |")
    return "\n".join(out)


def baseline_overall():
    out = ["| chunker | mode | n | Recall@5 | Recall@10 (95% CI) | MRR (95% CI) |", "|---|---|---|---|---|---|"]
    for r in ROWS:
        p = ("results", r, "overall")
        c, m = r.split("/")
        out.append(f"| {c} | {m} | {V(RB, p + ('n',), '{}')} | {V(RB, p + ('recall@5',))} | {V(RB, p + ('recall@10',))} "
                   f"({CI(RB, p)}) | {V(RB, p + ('mrr',))} ({CI(RB, p, 'mrr_ci95')}) |")
    return "\n".join(out)


def baseline_by_type():
    z = sizes()
    out = [f"| row | exact_term (n={z['exact_term']}) R@10 (CI) / MRR | mixed (n={z['mixed']}) R@10 (CI) / MRR | conceptual (n={z['conceptual']}) R@10 (CI) / MRR |", "|---|---|---|---|"]
    for r in ROWS:
        cells = []
        for t in TYPES:
            p = ("results", r, "by_type", t)
            cells.append(f"{V(RB, p + ('recall@10',), '{:.2f}')} ({ci_cell(RB, p)}) / {V(RB, p + ('mrr',), '{:.2f}')}")
        out.append(f"| {r} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def weights_table():
    z = sizes()
    out = [f"| row | n | Recall@10 (95% CI) | conceptual R@10 (n={z['conceptual']}) |", "|---|---|---|---|"]
    for ch in ["fixed", "heading"]:
        r = f"{ch}/dense"
        p = ("results", r, "overall")
        out.append(f"| {r} (reference, no fusion) | {V('rrf_weights.json', p + ('n',), '{}')} | {V('rrf_weights.json', p + ('recall@10',))} "
                   f"({CI('rrf_weights.json', p)}) | {V('rrf_weights.json', ('results', r, 'by_type', 'conceptual', 'recall@10'), '{:.2f}')} |")
        for w in ["w1", "w1.5", "w2"]:
            r = f"{ch}/hybrid {w}"
            p = ("results", r, "overall")
            label = mark(r, "result", "eval/results/rrf_weights.json", f"results > {r}", "row label (key name)")
            out.append(f"| {label} | {V('rrf_weights.json', p + ('n',), '{}')} | {V('rrf_weights.json', p + ('recall@10',))} "
                       f"({CI('rrf_weights.json', p)}) | {V('rrf_weights.json', ('results', r, 'by_type', 'conceptual', 'recall@10'), '{:.2f}')} |")
    return "\n".join(out)


def cio(c, k):
    lo, hi = J(AE)["configs"][c]["ci"][k]["ci95"]
    return mark(f"{lo:.3f}-{hi:.3f}", "result", f"eval/results/{AE}", f"configs > {c} > ci > {k} > ci95", "95% CI")


def answer_table():
    out = ["| config | answerable answered | false refusals | correct refusals (unanswerable) | answered when it should refuse | strict faithfulness (95% CI) | lenient | citation precision (95% CI) |", "|---|---|---|---|---|---|---|---|"]
    for c in ["heading/hybrid", "heading/dense"]:
        b = ("configs", c)
        s, ci = b + ("summary",), b + ("ci",)
        n_ans, fr = J(AE)["configs"][c]["summary"]["n_answerable"], J(AE)["configs"][c]["summary"]["false_refusals"]
        answered = X(f"{n_ans - fr} of {n_ans}", f"eval/results/{AE}", f"configs > {c} > summary > n_answerable - false_refusals", "answered answerable questions")
        out.append(
            f"| {c} | {answered} ({V(AE, ci + ('answer_coverage', 'value'))}; CI {cio(c, 'answer_coverage')}) | "
            f"{V(AE, s + ('false_refusals',), '{}')} | {V(AE, s + ('correct_refusals',), '{}')} of {V(AE, s + ('n_unanswerable',), '{}')} | "
            f"{V(AE, s + ('answered_unanswerable',), '{}')} | "
            f"{V(AE, ci + ('faithfulness_strict', 'value'))} ({cio(c, 'faithfulness_strict')}; "
            f"{V(AE, ci + ('faithfulness_strict', 'denominator'), '{}')} sentences, {V(AE, ci + ('faithfulness_strict', 'units'), '{}')} answers) | "
            f"{V(AE, ci + ('faithfulness_lenient', 'value'))} | "
            f"{V(AE, ci + ('citation_precision', 'value'))} ({cio(c, 'citation_precision')}; "
            f"{V(AE, ci + ('citation_precision', 'denominator'), '{}')} citations) |")
    return "\n".join(out)


def eval_costs():
    gen = [json.loads(line) for line in (RES / "answer_eval_generation.jsonl").read_text().splitlines()]
    ver = [json.loads(line) for line in (RES / "answer_eval_verification.jsonl").read_text().splitlines()]
    vc = {}
    for v in ver:  # the one failed attempt (e007) logged an error and no cost
        vc[(v["config"], v["qid"])] = vc.get((v["config"], v["qid"]), 0) + v.get("cost_usd", 0)
    ans, ref = [], []
    for g in gen:
        k = (g["config"], g["qid"])
        (ans if k in vc else ref).append(g["cost_usd"] + vc.get(k, 0))
    return ans, ref, sum(g["cost_usd"] for g in gen) + sum(v.get("cost_usd", 0) for v in ver)


# ---------------------------------------------------------------- values used in prose
def build():
    P = {}
    P["z"] = sizes()
    p = ("results", "heading/hybrid", "overall")
    rob = lambda r, s: V(RS, ("rows", r, "slices", s, "recall@10"))  # noqa: E731
    P["bm_c_f"], P["bm_c_h"] = rob("fixed/bm25", "conceptual"), rob("heading/bm25", "conceptual")
    P["de_b_f"], P["de_b_h"] = rob("fixed/dense", "bare_term"), rob("heading/dense", "bare_term")
    P["hy_b_f"], P["hy_b_h"] = rob("fixed/hybrid", "bare_term"), rob("heading/hybrid", "bare_term")
    P["de_c_f"], P["de_c_h"] = rob("fixed/dense", "conceptual"), rob("heading/dense", "conceptual")
    P["hy_c_f"], P["hy_c_h"] = rob("fixed/hybrid", "conceptual"), rob("heading/hybrid", "conceptual")
    P["de_o_h"] = V(RB, ("results", "heading/dense", "overall", "recall@10"))
    P["hy_o_h"] = V(RB, ("results", "heading/hybrid", "overall", "recall@10"))
    P["n"] = V(RB, p + ("n",), "{}")
    P["nq"] = V(AE, ("configs", "heading/hybrid", "summary", "n_questions"), "{}")
    P["nu"] = V(RB, ("meta", "n_unanswerable"), "{}")
    for tag, t in (("p", "overall"), ("c", "conceptual")):
        P[tag + "w"], P[tag + "t"], P[tag + "l"] = (V(RB, ("paired", "heading: hybrid vs dense", t, k), "{}") for k in ("win", "tie", "loss"))
    P["exh"] = V("bare_term.json", ("results", "heading/bm25", "overall", "exhausted"), "{}")
    P["exh_miss"] = V("bare_term.json", ("results", "heading/bm25", "overall", "exhausted_missed"), "{}")
    P["exh_n"] = P["z"]["bare"]
    P["pages"] = V("chunk_stats.json", ("pages",), "{}")
    P["cf"], P["ch"] = V("chunk_stats.json", ("fixed", "chunks"), "{:,}"), V("chunk_stats.json", ("heading", "chunks"), "{:,}")
    P["wn"] = V("chunk_stats.json", ("whats_next_sections_removed",), "{}")
    P["wnt"] = V("chunk_stats.json", ("whats_next_tokens_removed",), "{:,}")
    P["ent"] = V("chunk_stats.json", ("entities_decoded",), "{:,}")
    P["tmed_f"] = V("chunk_stats.json", ("fixed", "tokens_median"), "{:.0f}")
    P["tmed_h"] = V("chunk_stats.json", ("heading", "tokens_median"), "{:.0f}")
    P["tmax_h"] = V("chunk_stats.json", ("heading", "tokens_max"), "{}")
    emb = ("mapping", "rag-docs", "mappings", "properties", "embedding")
    P["idx"] = V("mapping.json", emb + ("index_options", "type"), "{}", "effective index_options")
    P["dims"] = V("mapping.json", emb + ("dims",), "{}")
    st = ("meta", "settings")
    P["esv"] = V("native_rrf_check.json", ("meta", "es_version"), "{}")
    P["emb"] = V(RB, st + ("embed_model",), "{}")
    P["pool"] = V(RB, st + ("pool",), "{}")
    P["knn_k"] = V(RB, st + ("knn", "k"), "{}")
    P["knn_nc"] = V(RB, st + ("knn", "num_candidates"), "{}")
    P["rrfk"] = V(RB, st + ("rrf_k",), "{}")
    P["boot"] = V(RB, st + ("bootstrap", "n"), "{:,}")
    P["bm_fields"] = ", ".join(f"`{mark(f, 'result', 'eval/results/' + RB, f'meta > settings > bm25_fields[{i}]', 'BM25 field boost')}`"
                               for i, f in enumerate(dig(RB, st + ("bm25_fields",))))
    cs = "docs/CORPUS.md"
    P["sha"] = D(re.search(r"Commit SHA: `([0-9a-f]{40})`", (ROOT / cs).read_text()).group(1), cs, "pinned corpus commit (regex-read by this script)")
    P["headless"] = D(re.search(r"the (\d+) headless include partials", (ROOT / cs).read_text()).group(1), cs, "headless include partials excluded (regex-read)")
    for ch in ("fixed", "heading"):
        for m in ("dense", "hybrid"):
            P[f"io_{ch}_{m}_a"] = V("index_options.json", ("results", f"{ch}/{m} [bbq_hnsw]", "overall", "recall@10"))
            P[f"io_{ch}_{m}_b"] = V("index_options.json", ("results", f"{ch}/{m} [hnsw]", "overall", "recall@10"))
        for k in ("n", "first_rank_identical", "top10_chunks_identical_order"):
            P[f"nr_{ch}_{k}"] = V("native_rrf_check.json", ("summary", ch, k), "{}")
    P["nr_exp"] = X(dig("native_rrf_check.json", ("meta", "license", "expiry"))[:10], "eval/results/native_rrf_check.json", "meta > license > expiry (date part)", "trial expiry")
    P["fh_f"], P["fh_h"] = V(RB, ("results", "fixed/hybrid", "overall", "recall@10")), V(RB, ("results", "heading/hybrid", "overall", "recall@10"))
    P["fd_f"], P["fd_h"] = V(RB, ("results", "fixed/dense", "overall", "recall@10")), V(RB, ("results", "heading/dense", "overall", "recall@10"))
    for c, k in (("heading/hybrid", "h"), ("heading/dense", "d")):
        s = ("configs", c, "summary")
        P[f"fr_{k}"] = V(AE, s + ("false_refusals",), "{}")
        P[f"cr_{k}"] = V(AE, s + ("correct_refusals",), "{}")
        P[f"ctx_{k}"] = V(AE, s + ("context_has_expected",), "{}")
    P["nun"] = V(AE, ("configs", "heading/hybrid", "summary", "n_unanswerable"), "{}")
    P["au"] = V(AE, ("configs", "heading/hybrid", "summary", "answered_unanswerable"), "{}")
    oc = ("paired_hybrid_vs_dense", "answerable_26", "outcomes")
    P["po"], P["ph"], P["pd"], P["pb"] = (V(AE, oc + (k,), "{}") for k in ("both_answered", "only_hybrid_answered", "only_dense_answered", "both_refused"))
    P["fw"], P["ft"], P["fl"] = (V(AE, ("paired_hybrid_vs_dense", "answerable_26", "faithfulness_both_verified", k), "{}") for k in ("win", "tie", "loss"))
    P["ctxm"] = V(AE, ("meta", "context", "max_chunks"), "{}")
    P["ctxp"] = V(AE, ("meta", "context", "per_doc"), "{}")
    P["am"], P["vm"], P["rub"] = (V(AE, ("meta", k), "{}") for k in ("answer_model", "verifier_model", "rubric"))
    P["run_cost"] = V(AE, ("meta", "run_cost_usd_reported"), "${:.4f}")
    nu = dig(AE, ("configs", "heading/hybrid", "summary", "n_unanswerable"))
    P["lb"] = X(f"{0.025 ** (1 / nu):.2f}", "computed here", f"0.025 ** (1/{nu})", "exact 95% lower bound for 4 of 4 refusals")
    mh = "verify_mutation_haiku.json"
    P["mn"] = V(mh, ("n",), "{}")
    P["mw_no"], P["mw_n"] = V(mh, ("summary", "wrong_pairs", "no"), "{}"), V(mh, ("summary", "wrong_pairs", "n"), "{}")
    P["mcv_n"], P["mcv_y"] = V(mh, ("summary", "controls_verbatim", "n"), "{}"), V(mh, ("summary", "controls_verbatim", "yes"), "{}")
    P["mcp_n"], P["mcp_y"] = V(mh, ("summary", "controls_paraphrase", "n"), "{}"), V(mh, ("summary", "controls_paraphrase", "yes"), "{}")
    P["go_c_med"], P["go_e_med"] = V("golden_overlap.json", ("by_type", "conceptual", "ratio_median")), V("golden_overlap.json", ("by_type", "exact_term", "ratio_median"))
    P["go_c_rare"] = V("golden_overlap.json", ("by_type", "conceptual", "rare_terms_mean"), "{:.1f}")
    P["go_c_copy"] = V("golden_overlap.json", ("by_type", "conceptual", "copied_phrase"), "{}")
    ans, ref, tot = eval_costs()
    lg = "eval/results/answer_eval_generation.jsonl + answer_eval_verification.jsonl"
    P["a_n"] = X(str(len(ans)), lg, "questions with a verification record", "answered questions (both configs)")
    P["a_min"] = X(f"${min(ans):.4f}", lg, "min(generation + verification cost_usd)", "per-answered-question cost")
    P["a_med"] = X(f"${statistics.median(ans):.4f}", lg, "median(generation + verification cost_usd)", "per-answered-question cost")
    P["a_max"] = X(f"${max(ans):.4f}", lg, "max(generation + verification cost_usd)", "per-answered-question cost")
    P["r_n"] = X(str(len(ref)), lg, "questions without a verification record", "refused questions (both configs)")
    P["r_min"] = X(f"${min(ref):.4f}", lg, "min(generation cost_usd)", "refusal cost")
    P["r_max"] = X(f"${max(ref):.4f}", lg, "max(generation cost_usd)", "refusal cost")
    P["tot"] = X(f"${tot:.4f}", lg, "sum of all cost_usd in both logs", "answer-eval total from logs")
    P["spend"] = D("about $1.1", "STATUS.md 'Spend so far'", "whole-project API spend; the ledger's 1.0776 excludes the clean-clone embedding (0.0534)")
    P["ledger"] = D("1.0776", "STATUS.md / NOTES.md Phase 8 step 2", "spend-ledger value after the live API calls")
    P["clone_emb"] = D("$0.0534", "eval/results/clean_clone_check.md; STATUS.md", "clean-clone embedding, run from the host")
    P["live_ask"] = D("$0.0173", "NOTES.md Phase 8 step 2", "one live /ask, answerable, 12 sentences")
    P["live_ref"] = D("$0.0103", "NOTES.md Phase 8 step 2", "one live /ask refusal")
    P["live_worst"] = D("$0.053", "NOTES.md Phase 8 step 2", "worst-case estimate for one /ask")
    P["moved"] = D("1 of 104", "eval/results/clean_clone_check.md", "dense/hybrid first ranks moved in the clean clone")
    # typed constants: configuration or description, each with where it is stated
    P["docs_body"] = V("chunk_stats.json", ("fixed", "docs"), "{}")
    nr = lambda k: sum(dig("native_rrf_check.json", ("summary", ch, k)) for ch in ("fixed", "heading"))  # noqa: E731
    nsrc = "eval/results/native_rrf_check.json"
    P["nr_first"] = X(str(nr("first_rank_identical")), nsrc, "summary > fixed + heading > first_rank_identical", "sum over both chunkers")
    P["nr_top"] = X(str(nr("top10_chunks_identical_order")), nsrc, "summary > fixed + heading > top10_chunks_identical_order", "sum over both chunkers")
    P["nr_tot"] = X(str(nr("n")), nsrc, "summary > fixed + heading > n", "sum over both chunkers")
    for ch in ("fixed", "heading"):
        for m in ("hybrid", "bm25"):
            P[f"bt_{m}_mrr_{ch}"] = V("bare_term.json", ("results", f"{ch}/{m}", "overall", "mrr"))
    P["t_one"] = T("1.000", "Recall@10 value at which the bootstrap interval degenerates", "definition in the note below the bare-term table")
    P["t_zero"] = T("0.000", "Recall@10 value at which the bootstrap interval degenerates", "definition in the note below the bare-term table")
    P["t_400"] = T("400", "fixed chunker target tokens", "docs/BUILD_GUIDE.md Phase 1")
    P["t_2"] = T("2", "two chunkers", "docs/BUILD_GUIDE.md")
    P["t_10"] = T("10", "top-10 list in the native-vs-Python comparison", "eval/results/native_rrf_check.md")
    P["t_30d"] = T("30", "days of the trial licence", "docs/BUILD_GUIDE.md licence section")
    P["t_403"] = T("403", "HTTP status of the Enterprise-gated rrf retriever on a Basic licence", "docs/BUILD_GUIDE.md licence section")
    P["t_w"] = T("1 / 1.5 / 2", "dense weights tried (BM25 weight 1)", "eval/results/rrf_weights.md")
    P["t_w1"] = T("1", "BM25 weight", "eval/results/rrf_weights.md")
    P["t_cost005"] = T("$0.05", "approximate paid embedding step", "docs/SETUP.md cost table")
    P["t_ids"] = T("c009, c010, c002", "golden question ids", "eval/results/failure_analysis.md")
    P["t_ccby"] = T("4.0", "CC BY licence version", "docs/CORPUS.md")
    P["t_top50"] = T("50", "reranker candidate depth (a proposal, not a result)", "docs/BUILD_GUIDE.md Stretch")
    P["t_r1"] = T("1", "human labelling round that had no controls", "STATUS.md 'Checkpoint 4: CLOSED'")
    P["t_r23"] = T("2 and 3", "human labelling rounds that failed their pre-registered controls", "STATUS.md 'Checkpoint 4: CLOSED'")
    return P


def limitations():
    quoted = text_between("STATUS.md", "## README limitations", r'^- "(.+)"$')
    plus = text_between("STATUS.md", "## README limitations", r"^- Plus the earlier ones: (.+)$")
    q = [D(t, "STATUS.md 'README limitations' (copied verbatim)", "limitation text") for t in quoted]
    return q, D(plus[0], "STATUS.md 'README limitations' (copied verbatim)", "limitation text")


def readme(P):
    q, plus = limitations()
    z = P["z"]
    return f"""# rag-hybrid: hybrid search RAG over the Kubernetes docs, with an evaluation harness

A RAG service over {P['pages']} Kubernetes documentation pages ({P['docs_body']} with body text): Elasticsearch BM25 and kNN, fused with a reciprocal-rank-fusion function implemented in this repo, answers with validated citations, and a claim-level citation verifier. The repo is as much an evaluation harness for comparing retrieval modes as it is a service. Every figure below is generated by [`scripts/make_readme_tables.py`](scripts/make_readme_tables.py) from files in [`eval/results/`](eval/results/); the sources are listed in [`docs/NUMBERS_AUDIT.md`](docs/NUMBERS_AUDIT.md).

> **Caveats.** Only {P['n']} answerable questions and no held-out set: every result is on one frozen golden set, so most differences between modes are within the noise.
> The citation verifier has not been validated against human judgement, so the faithfulness figures are verifier outputs, not measured accuracy.

## Architecture
- One Elasticsearch {P['esv']} index (`rag-docs`) holding both chunkers' output, separated by a `chunker` field: **fixed** ({P['cf']} chunks, {P['t_400']}-token target) and **heading-aware** ({P['ch']} chunks). `embedding` is a {P['dims']}-d `dense_vector` (`{P['emb']}`); effective `index_options` is `{P['idx']}`.
- Three retrieval modes per request: **BM25** ({P['bm_fields']}), **dense** kNN, **hybrid** = Python RRF (k={P['rrfk']}) over the two {P['pool']}-chunk windows, then dedupe to documents.
- `/ask`: top {P['ctxm']} chunks (max {P['ctxp']} per page) to `{P['am']}`, structured sentences with citations, validated in code; if the context lacks the answer it must refuse. `{P['vm']}` then judges each (sentence, citation) pair against the cited text (rubric `{P['rub']}`: it lists claims, and the verdict is derived in code).
- FastAPI (`/search`, `/ask`), spend ledger with a hard limit, Docker Compose (ES, API, Kibana behind a profile).

## The finding
Each retriever fails on a different kind of query, and the full-question slices hide it. Recall@10 is shown with MRR, per chunker and mode (slice sizes are small, so see the intervals in the next sections):

{robustness_table()}

- **BM25 fails on paraphrased symptoms.** Conceptual questions deliberately avoid the page's vocabulary: BM25 Recall@10 is {P['bm_c_f']} (fixed) and {P['bm_c_h']} (heading).
- **Dense fails on pasted identifiers.** With only the exact term as the query (`bare_term`), dense falls to {P['de_b_f']} / {P['de_b_h']}; BM25 and hybrid hold {P['hy_b_f']} / {P['hy_b_h']}. With the full question around the term, dense is at ceiling on exact_term and mixed.
- **Hybrid does not win overall, and its worst slice is not the best worst slice.** Hybrid's worst slice (conceptual, {P['hy_c_f']} / {P['hy_c_h']}) is far above BM25's but **below dense's** ({P['de_c_f']} / {P['de_c_h']}). Overall Recall@10, heading chunker: dense {P['de_o_h']}, hybrid {P['hy_o_h']} (n = {P['n']}, intervals overlap). Paired per question, hybrid vs dense (heading): {P['pw']} better, {P['pt']} equal, {P['pl']} worse; on conceptual questions {P['cw']} / {P['ct']} / {P['cl']} (better / equal / worse). The case for hybrid on this set is that it keeps the identifier-only queries that dense loses, at a cost on paraphrased ones; it is not a claim that hybrid beats dense.

Bare-term diagnostic (the {z['bare']} exact_term + mixed questions with the exact term alone as the query; same expected pages). BM25's list was exhausted before {P['pool']} chunks for {P['exh']} of {P['exh_n']} heading queries (rare identifiers); of those, {P['exh_miss']} missed the expected page:

{bare_table()}

`exact` is the Clopper-Pearson 95% interval, shown where Recall@10 is exactly {P['t_one']} or {P['t_zero']} and the bootstrap interval collapses to a point; it treats each question as a hit or a miss (here all hits or all misses).
On bare terms hybrid's MRR is below BM25's (fixed {P['bt_hybrid_mrr_fixed']} vs {P['bt_bm25_mrr_fixed']}, heading {P['bt_hybrid_mrr_heading']} vs {P['bt_bm25_mrr_heading']}): fusion trades peak rank for robustness, so it mostly keeps the expected page in the top ten, but not always near the top.

## Baseline (the headline)
Frozen golden set ([`eval/golden.jsonl`](eval/golden.jsonl)) of {P['nq']} questions ({P['n']} answerable + {P['nu']} unanswerable), document-level metrics, no tuning, bootstrap 95% intervals resampling questions ({P['boot']} draws). Settings: pool {P['pool']}, kNN k={P['knn_k']} with num_candidates {P['knn_nc']}, RRF k={P['rrfk']}, `{P['idx']}`.

{baseline_overall()}

By question type (n = {z['exact_term']} / {z['mixed']} / {z['conceptual']}, so the intervals are wide; read differences with care; `exact` as defined above):

{baseline_by_type()}

## Sensitivity analyses (not tuning; no winner was picked)
The golden set is frozen and there is no held-out split, so everything below is sensitivity analysis on the same {P['n']} questions. None of it changes the headline above.
- **Weighted RRF** (dense weight {P['t_w']}, BM25 weight {P['t_w1']}; all reported, none chosen):

{weights_table()}

- **`{P['idx']}` vs explicit `hnsw`** (same vectors; Recall@10 dense/hybrid): fixed {P['io_fixed_dense_a']} vs {P['io_fixed_dense_b']} / {P['io_fixed_hybrid_a']} vs {P['io_fixed_hybrid_b']}; heading {P['io_heading_dense_a']} vs {P['io_heading_dense_b']} / {P['io_heading_hybrid_a']} vs {P['io_heading_hybrid_b']}. The quantised default cost nothing measurable here.
- **Failure analysis** ([`failure_analysis.md`](eval/results/failure_analysis.md)): three conceptual questions ({P['t_ids']}) whose answer is one sentence inside a longer section, phrased without that sentence's key nouns. They are hard, not golden-set errors.

## Answer evaluation
Pre-registered configs, {P['nq']} questions, context top {P['ctxm']} chunks / max {P['ctxp']} per page. The verifier judges each (sentence, citation) pair. **Strict faithfulness** = share of sentences with at least one cited excerpt judged `yes`; **lenient** = at least one judged `yes` or `partial`; **citation precision** = share of cited pairs judged `yes`. All three measure support by the cited excerpts, **not correctness**.

{answer_table()}

- Answered-or-refused is a retrieval story: context contained an expected page for {P['ctx_h']} (hybrid) and {P['ctx_d']} (dense) answerable questions, and most false refusals ({P['fr_h']} hybrid, {P['fr_d']} dense) follow a retrieval miss. Coverage should be read next to faithfulness: a system that refuses more can look more faithful.
- Paired, answerable questions: both answered {P['po']}, only hybrid {P['ph']}, only dense {P['pd']}, both refused {P['pb']}. Where both were verified, hybrid's strict faithfulness was higher on {P['fw']}, equal on {P['ft']}, lower on {P['fl']}. No winner.
- **Refusals, n = {P['nun']}:** both configs refused all {P['cr_h']} of {P['nun']} unanswerable questions (answered-when-unanswerable: {P['au']}). Two ask for the default of a kube-controller-manager and a kube-proxy flag whose names appear in no indexed chunk; for both, the retrieved context contained the related component configuration pages ([`answer_eval_review.md`](eval/results/answer_eval_review.md)), so they test a refusal next to topical pages. The other two are off-topic (sourdough, Jupiter). Not tested: unanswerable questions whose neighbouring page states a similar but different value, paraphrased unanswerable questions, or enough of them to estimate a rate (with n = {P['nun']} the exact 95% lower bound on the refusal rate is {P['lb']}).

## Design decisions and what I would change
- **Python RRF is the default** because the native `rrf` retriever is Enterprise-gated ({P['t_403']} on a Basic licence). A cross-check on a {P['t_30d']}-day trial (expires {P['nr_exp']}) compared the two on {P['nr_fixed_n']} questions x {P['t_2']} chunkers: first expected-page rank identical in {P['nr_first']} of {P['nr_tot']}; top-{P['t_10']} chunk order identical in {P['nr_top']} of {P['nr_tot']}. The differences are exact RRF score ties that Elasticsearch orders differently (float32 scores vs the repo's exact fractions), see [`native_rrf_check.md`](eval/results/native_rrf_check.md).
- **Chunking:** fixed vs heading-aware is within noise on this set (hybrid Recall@10 {P['fh_f']} vs {P['fh_h']}, dense {P['fd_f']} vs {P['fd_h']}; n = {P['n']}). Medians are {P['tmed_f']} and {P['tmed_h']} tokens; the heading chunker's maximum is {P['tmax_h']}.
- **Corpus cleaning:** the "What's next" sections ({P['wn']} sections, {P['wnt']} tokens) are stripped because they are navigation links to other pages, not answer content; {P['headless']} headless include partials are excluded because they are not public pages; {P['ent']} HTML entities are decoded outside code blocks.
- **Verifier:** claims-based. The model only lists claims and whether the cited text states each; the verdict is computed in code. The first rubric asked for the verdict directly and its `partial` became a loose bucket (faithful paraphrases marked partial).
- **Would change:** a held-out question set, a larger golden set, near-miss unanswerable questions, a cross-encoder reranker, and a human-validated verifier.

## Cost
Measured in the answer evaluation ({P['am']} + {P['vm']}, both configs): {P['a_n']} answered questions cost {P['a_min']} to {P['a_max']} each (median {P['a_med']}); {P['r_n']} refusals cost {P['r_min']} to {P['r_max']}. The whole run was {P['run_cost']} reported ({P['tot']} summed from the logs). Live `/ask` costs vary with answer length: one answerable call was {P['live_ask']} (worst-case estimate {P['live_worst']}) and one refusal {P['live_ref']}. Retrieval evaluation makes no LLM calls. **Whole-project spend: {P['spend']}** (the spend ledger shows {P['ledger']} because the {P['clone_emb']} clean-clone embedding ran from the host).

## How this was built
Built with Claude Code under my direction. I set the scope and the rules, defined and froze the golden set, made the design decisions and reviewed the outputs; every commit lists Claude as co-author.

## Limitations
- {q[0]}
- {q[1]}
- Also: {plus}
- Three human labelling rounds of the verifier were attempted; round {P['t_r1']} had no controls and was inconsistent, rounds {P['t_r23']} failed their own pre-registered control checks. No human-labelled verifier accuracy is claimed anywhere. On the {P['mn']}-pair mutation dev set the verifier caught {P['mw_no']} of {P['mw_n']} wrong pairs and gave `yes` to {P['mcv_y']} of {P['mcv_n']} verbatim and {P['mcp_y']} of {P['mcp_n']} paraphrased controls, but that set was built from the verifier's own earlier failures and the rubric was written after seeing them, so those scores are optimistic by construction.
- Only {P['n']} answerable questions, one corpus, one snapshot ({P['pages']} pages), so most differences have overlapping intervals.
- **Golden set provenance:** questions were drafted with LLM help from verified corpus excerpts, reworded against lexical overlap rules, the expected pages were checked against page text (not retrieval output) and approved by me, and the set was frozen before any evaluation. Conceptual questions deliberately avoid page vocabulary (median word-overlap ratio {P['go_c_med']} vs {P['go_e_med']} for exact_term; {P['go_c_rare']} shared rare terms on average, {P['go_c_copy']} copied phrases), which is the hardest case for BM25 and favours dense; overlap is a lexical proxy, not a guarantee.
- **Reproducibility is at document level.** Elasticsearch breaks equal-score ties by internal document id (indexing order), so chunk order among exact ties can differ between builds. A clean-clone rebuild reproduced BM25 rows exactly and moved {P['moved']} dense/hybrid first ranks ([`clean_clone_check.md`](eval/results/clean_clone_check.md)).
- **Outbound network:** Docker Compose cannot allowlist egress hosts, so the API container has default outbound access (it needs only ES and the two provider APIs). Mitigations: non-root, read-only filesystem, capabilities dropped, no secrets in the image, spend ledger, loopback-only ports.
- Docker images are pinned by tag (Python base by digest) and have not been vulnerability-scanned.
- **Two spend ledgers exist** (Docker volume `rag-hybrid_apidata` and host `data/api/spend_ledger.json`); Docker is the supported mode. The limit is per ledger, not global.

## Security
The API has no authentication, no TLS and no rate limiting beyond the spend ledger, and Elasticsearch runs with its security features off. Both are meant for localhost only: Compose publishes them on the loopback interface, and `/ask` spends your API credits. Do not expose these ports to a network or the internet. If you need remote access, put an authenticating reverse proxy in front and keep the spend limit.

## Reproduce
Follow [`docs/SETUP.md`](docs/SETUP.md) (pinned dependencies, corpus fetch with checks, paid embedding step about {P['t_cost005']}, then `pytest`). Corpus: [kubernetes/website](https://github.com/kubernetes/website) at commit `{P['sha']}`, CC BY {P['t_ccby']}, paths `content/en/docs/{{concepts,tasks,reference}}` (scope in [`docs/CORPUS.md`](docs/CORPUS.md)). Build spec: [`docs/BUILD_GUIDE.md`](docs/BUILD_GUIDE.md). Decisions and deviations: [`NOTES.md`](NOTES.md). Code is MIT-licensed; the Kubernetes documentation is CC BY {P['t_ccby']}, fetched at the pinned commit and not redistributed in this repo.

## Next steps
Reranker on the top {P['t_top50']}, query rewriting, a held-out question set with near-miss unanswerables, a human-validated verifier, and hooking this in as the `search_kb` tool of a support agent.
"""


# ---------------------------------------------------------------- finalize + audit
def finalize(text):
    """Strip the markers; return (clean text, occurrences with exact spans in the clean text)."""
    pat = re.compile(f"{S}(\\d+){M}(.*?){E}", re.S)
    out, occ, last, n = [], [], 0, 0
    for m in pat.finditer(text):
        gap = text[last:m.start()]
        out.append(gap)
        n += len(gap)
        t = m.group(2)
        occ.append({**ENTRIES[int(m.group(1))], "text": t, "start": n, "end": n + len(t)})
        out.append(t)
        n += len(t)
        last = m.end()
    out.append(text[last:])
    clean = "".join(out)
    assert not re.search(f"[{S}{M}{E}]", clean), "unbalanced marker"
    return clean, occ


def _count(keys):
    seen = {}
    for k in keys:
        seen[k] = seen.get(k, 0) + 1
    return seen


def audit_md(manifest):
    """The audit document, built only from the manifest."""
    occ = manifest["occurrences"]
    by = {k: [o for o in occ if o["kind"] == k] for k in ("result", "computed", "doc", "typed")}
    short = lambda t: t if len(t) <= 70 else t[:70] + "..."  # noqa: E731
    out = ["# Numbers audit", "",
           "Generated from `docs/numbers_manifest.json` by `scripts/make_readme_tables.py`. Every digit in `README.md` lies inside one of the spans recorded in that manifest; `tests/test_readme_numbers.py` enforces it.", "",
           f"{len(occ)} recorded spans in README.md: {len(by['result'])} from result files, {len(by['computed'])} computed from them, {len(by['doc'])} from prose docs, {len(by['typed'])} typed constants.", "",
           "## 1. From result files (and values computed from them)", "", "| value | source file | key path | note | uses |", "|---|---|---|---|---|"]
    for (t, s, k, lab, kind), n in _count((o["text"], o["source"], o["key"], o["label"], o["kind"]) for o in by["result"] + by["computed"]).items():
        out.append(f"| {t} | `{s}` | `{k}` | {lab}{' (computed)' if kind == 'computed' else ''} | {n} |")
    out += ["", "## 2. From prose docs (not machine-read from result files)", "", "| value | source | note | uses |", "|---|---|---|---|"]
    for (t, s, lab), n in _count((short(o["text"]), o["source"], o["label"]) for o in by["doc"]).items():
        out.append(f"| {t} | {s} | {lab} | {n} |")
    out += ["", "## 3. Typed constants (configuration or description, with where each is stated)", "", "| text | meaning | stated in | uses |", "|---|---|---|---|"]
    for (t, lab, s), n in _count((o["text"], o["label"], o["source"]) for o in by["typed"]).items():
        out.append(f"| {t} | {lab} | {s} | {n} |")
    return "\n".join(out) + "\n"


def main():
    text, occ = finalize(readme(build()))
    manifest = {"readme": "README.md", "occurrences": occ}
    (ROOT / "README.md").write_text(text)
    (ROOT / "docs" / "numbers_manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "docs" / "NUMBERS_AUDIT.md").write_text(audit_md(manifest))
    print(f"README.md: {len(text.splitlines())} lines; manifest: {len(occ)} spans")


if __name__ == "__main__":
    main()
