"""Checkpoint 4, round 3: an interactive blind labelling tool with a calibration warm-up and fresh hidden controls. No API calls.

    python -m eval.checkpoint4_round3 build     # creates the items, the hidden key and the practice set (refuses if labels exist)
    python -m eval.checkpoint4_round3 label     # the owner labels one item at a time: s / p / u (+ optional note), z = undo, q = quit; resumable
    python -m eval.checkpoint4_round3 score     # refuses until all 30 scored items are labelled

What the tool shows: the short rubric, the sentence and the cited excerpt. Nothing it displays or logs says which item is a control,
what the verifier decided, or where an item came from. Labels are written by the tool itself, keyed by an internal id the owner never types.

Calibration warm-up (6 practice pairs, never scored, disjoint from the scored items): after each answer the tool shows the expected label
and a one-line reason. Practice pairs come from unused verifier mutation-set items (changed-number, inverted claim, swapped citation,
verbatim-correct, faithful paraphrase) plus one authored `partial` case.

Scored set (shuffled with a new seed): 24 verifier-`yes` pairs not used in round 1 or 2, plus 6 fresh controls authored from excerpts used in
no earlier round: 2 contradicted (one changed number, one inverted claim; expected `unsupported`), 1 swapped citation (expected `unsupported`),
1 verbatim-correct and 2 faithful paraphrases (expected `supported`).

Pre-registered validity rule (as in round 2): if the owner mislabels more than 1 of the 6 controls (2 or more), the round is INVALID for judging
the verifier; `score` then reports the controls and stops. Otherwise it reports, in order: the controls; the false-yes rate over the 24 yes pairs
(not `supported`, and `unsupported` only) with exact 95% intervals; the distribution of the owner's labels over the verifier's `yes`.
"""
import argparse
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

from eval.checkpoint4 import KEY as KEY1, population
from eval.checkpoint4_round2 import KEY as KEY2, score as score_core
from eval.answer_eval import GEN_LOG, read_log
from eval.verify_mutation import build as build_mutations
from rag.verify import SNAPSHOT, load_row_chunks

DIR = Path("eval/checkpoint4/round3")
ITEMS, PRACTICE, KEY = DIR / "items.json", DIR / "practice.json", DIR / "key_do_not_open_until_labelled.json"
LABEL_LOG, PRACTICE_LOG = DIR / "labels.jsonl", DIR / "practice_log.jsonl"
SEED, N_YES = 7919, 24
KEYS = {"s": "supported", "p": "partial", "u": "unsupported"}

RUBRIC_SHORT = """Rubric: split the sentence into claims and judge each against the excerpt ALONE (not what you know about Kubernetes).
  s = supported    every claim is in the excerpt or directly implied (paraphrase counts)
  p = partial      some claims are in the excerpt and none is contradicted
  u = unsupported  the excerpt contradicts the sentence, or the sentence's main claim is absent"""


# -- the 6 fresh controls: authored from excerpts used in no earlier round (disjoint from round 2's controls and from the practice set) --------------
# (doc suffix, heading fragment) identifies the excerpt (a saved answer_eval context chunk); `edit` is the exact sentence shown.
CONTROLS = [
    {"source": "K1", "subtype": "changed number", "expected": "unsupported", "doc": "policy/resource-quotas", "heading": "How Kubernetes ResourceQuotas work",
     "sentence": "As an example policy, in a cluster with 32 GiB RAM and 16 cores, team A could use 20 GiB and 10 cores, team B 10 GiB and 8 cores, and 2 GiB and 2 cores could be held in reserve."},
    {"source": "K2", "subtype": "inverted claim", "expected": "unsupported", "doc": "bootstrap-tokens", "heading": "Authenticating with Bootstrap Tokens",
     "sentence": "Expired bootstrap tokens are still accepted for authentication, but they are ignored when the cluster-info ConfigMap is signed."},
    {"source": "K3", "subtype": "swapped citation", "expected": "unsupported", "doc": "administer-cluster/safely-drain-node", "heading": "Use `kubectl drain`",
     "sentence": "Clusters built with kubeadm often copy the `admin.conf` certificate into `$HOME/.kube/config`."},
    {"source": "K4", "subtype": "verbatim", "expected": "supported", "doc": "pod-scheduling-readiness", "heading": "Mutable Pod scheduling directives",
     "sentence": "At a high level, you can only tighten the scheduling directives of a Pod."},
    {"source": "K5", "subtype": "faithful paraphrase", "expected": "supported", "doc": "working-with-objects/namespaces", "heading": "When to Use Multiple Namespaces",
     "sentence": "Namespaces are intended for environments in which many users from multiple teams or projects share a cluster, so a cluster used by only a few to tens of users does not need them at all."},
    {"source": "K6", "subtype": "faithful paraphrase", "expected": "supported", "doc": "compositepodgroup-api/_index", "heading": "How it fits together",
     "sentence": "A Workload is a long-lived policy template, whereas CompositePodGroup and PodGroup resources hold the scheduling state of each runtime instance."},
]

# Practice pairs: (id, mutation-set item or None, authored sentence or None, expected label, reason shown after the answer)
PRACTICE_SPEC = [
    ("changed number", None, "On a node whose host OS allows at most 262144 PIDs and which is expected to host fewer than 250 Pods, each Pod can be given a budget of 2000 PIDs.", "unsupported",
     "The excerpt's example gives each Pod a budget of 1000 PIDs, so the number in the sentence is contradicted."),
    ("inverted claim", "M08", None, "unsupported", "The excerpt says per-Pod PID limiting does not ensure this; the sentence says it does, so it is contradicted."),
    ("swapped citation", "M04", None, "unsupported", "The excerpt is about API server tracing; it says nothing about API Priority and Fairness or concurrency limits, so the main claim is absent."),
    ("verbatim", "C03", None, "supported", "The sentence is copied from the excerpt's note about the low default PIDs limit."),
    ("faithful paraphrase", "P01", None, "supported", "It restates the excerpt's first sentence (limiting how many PIDs a Pod can use) in other words."),
    ("partial", None, "Administrators can reserve some allocatable PIDs for the operating system and daemons, and the scheduler automatically adds that reservation to every Pod's PID budget.", "partial",
     "The first half is in the excerpt; the scheduler claim is not there but is not contradicted either."),
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def control_excerpts() -> list[dict]:
    gens = read_log(GEN_LOG, lambda r: (r["config"], r["qid"]))
    chunks = [ch for g in gens.values() for ch in g["chunks"]]
    out = []
    for c in CONTROLS:
        hit = next((ch for ch in chunks if ch["doc_id"].endswith(c["doc"]) and c["heading"] in ch["heading_path"]), None)
        if hit is None:
            raise ValueError(f"control {c['source']}: excerpt not found")
        out.append({**c, "excerpt": hit["content"], "kind": "control_wrong" if c["expected"] == "unsupported" else "control_correct"})
    return out


def practice_items() -> list[dict]:
    rows = [json.loads(l) for l in open("eval/results/generation_log.jsonl", encoding="utf8")]
    snap = json.loads(Path(SNAPSHOT).read_text())["chunks"]
    found = {m["id"]: (ri, m) for ri, ms in build_mutations(rows).items() for m in ms}
    pid_excerpt = load_row_chunks(rows[0], snap)[2]
    out = []
    for kind, src, text, expected, reason in PRACTICE_SPEC:
        if src:
            ri, m = found[src]
            sentence, excerpt = m["sentence"], load_row_chunks(rows[ri], snap)[m["citations"][0]]
        else:
            sentence, excerpt = text, pid_excerpt
        out.append({"kind": kind, "sentence": sentence, "excerpt": excerpt, "expected": expected, "reason": reason})
    return out


def used_before() -> tuple[set, set, set]:
    """(pair keys, sentences, normalised excerpts) already used in rounds 1 and 2, including round 2's controls."""
    keys, sents, excs = set(), set(), set()
    pop = population()
    by = {(p["config"], p["qid"], p["sentence_no"], p["citation"]): p for p in pop}
    for f in (KEY1, KEY2):
        for v in json.loads(f.read_text())["items"].values():
            if "config" in v:
                k = (v["config"], v["qid"], v["sentence_no"], v["citation"])
                keys.add(k)
                sents.add(by[k]["sentence"])
                excs.add(_norm(by[k]["excerpt"]))
    return keys, sents, excs


def draw(yes: list[dict], controls: list[dict], seed: int = SEED, n_yes: int = N_YES) -> list[dict]:
    rng = random.Random(seed)
    items = [{**p, "kind": "yes_pair"} for p in rng.sample(yes, n_yes)] + list(controls)
    rng.shuffle(items)
    return items


def build_files() -> int:
    if LABEL_LOG.exists() and LABEL_LOG.stat().st_size:
        print(f"{LABEL_LOG} already has answers; refusing to rebuild over them")
        return 1
    ctl, prac = control_excerpts(), practice_items()
    keys, sents, excs = used_before()
    ctl_exc = {_norm(c["excerpt"]) for c in ctl}
    ctl_sent = {c["sentence"] for c in ctl}
    prac_exc = {_norm(p["excerpt"]) for p in prac}
    prac_sent = {p["sentence"] for p in prac}
    pool = [p for p in population() if p["verifier"] == "yes" and (p["config"], p["qid"], p["sentence_no"], p["citation"]) not in keys
            and p["sentence"] not in sents | ctl_sent | prac_sent and _norm(p["excerpt"]) not in ctl_exc | prac_exc]
    items = draw(pool, ctl)
    rng = random.Random(SEED + 1)
    ids = [f"r3-{rng.getrandbits(32):08x}" for _ in items]
    DIR.mkdir(parents=True, exist_ok=True)
    ITEMS.write_text(json.dumps([{"id": i, "sentence": p["sentence"], "excerpt": p["excerpt"]} for i, p in zip(ids, items)], indent=1))
    PRACTICE.write_text(json.dumps([{"id": f"pr-{n}", **p} for n, p in enumerate(prac, 1)], indent=1))
    KEY.write_text(json.dumps({"seed": SEED, "n_yes": N_YES, "validity_rule": "invalid if more than 1 of the 6 controls is mislabelled",
                               "items": {i: ({k: p[k] for k in ("kind", "source", "subtype", "expected")} if p["kind"] != "yes_pair"
                                             else {k: p[k] for k in ("kind", "config", "qid", "sentence_no", "citation", "verifier")}) for i, p in zip(ids, items)}}, indent=1))
    LABEL_LOG.write_text("")
    PRACTICE_LOG.write_text("")
    print(f"built {len(items)} scored items ({N_YES} yes pairs from a pool of {len(pool)} + 6 controls) and {len(prac)} practice pairs in {DIR}/")
    return 0


# -- interactive labelling -----------------------------------------------------------------------------------------------------------
def _read_log(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf8").splitlines() if l.strip()] if path.exists() else []


def labelled(log: list[dict]) -> list[dict]:
    """Replay a log of answers and undos into the list of answers currently in force, in order."""
    stack: list[dict] = []
    for r in log:
        if r.get("undo"):
            if stack:
                stack.pop()
        else:
            stack = [a for a in stack if a["id"] != r["id"]] + [r]
    return stack


def _append(path: Path, rec: dict) -> None:
    with open(path, "a", encoding="utf8") as f:
        f.write(json.dumps({**rec, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}, ensure_ascii=False) + "\n")


def _show(out, header: str, item: dict) -> None:
    out("\n" + "=" * 78 + f"\n{header}\n" + "=" * 78)
    out(RUBRIC_SHORT + "\n")
    out("SENTENCE:\n  " + item["sentence"] + "\n")
    out("CITED EXCERPT:\n" + "-" * 78 + "\n" + item["excerpt"].rstrip() + "\n" + "-" * 78)


def _ask(inp, out, undo_ok: bool) -> str:
    while True:
        a = inp("\n[s]upported  [p]artial  [u]nsupported" + ("  [z] undo last answer" if undo_ok else "") + "  [q] quit > ").strip().lower()
        if a in KEYS or a == "q" or (a == "z" and undo_ok):
            return a
        out("Please answer s, p, u" + (", z" if undo_ok else "") + " or q.")


def run_practice(items: list[dict], log_path: Path, inp=input, out=print) -> bool:
    """Returns True when all practice pairs are answered. Answers are logged but never scored."""
    done = {r["id"] for r in _read_log(log_path)}
    todo = [it for it in items if it["id"] not in done]
    if todo and not done:
        out("Calibration warm-up: 6 practice pairs. After each answer you see the expected label and why. They are not scored.")
    for it in todo:
        _show(out, f"Practice {len(done) + 1} of {len(items)}", it)
        a = _ask(inp, out, undo_ok=False)
        if a == "q":
            out("Progress saved. Run the same command to resume.")
            return False
        _append(log_path, {"id": it["id"], "label": KEYS[a]})
        done.add(it["id"])
        out(f"\nExpected: {it['expected']}. {it['reason']}" + ("  (matches your answer)" if KEYS[a] == it["expected"] else "  (differs from your answer)"))
        inp("Press Enter to continue ")
    return True


def run_label(items: list[dict], log_path: Path, inp=input, out=print) -> bool:
    """One scored item at a time. Returns True when every item is labelled."""
    ids = [it["id"] for it in items]
    while True:
        cur = labelled(_read_log(log_path))
        got = {a["id"] for a in cur}
        nxt = next((it for it in items if it["id"] not in got), None)
        if nxt is None:
            out(f"\nAll {len(items)} items are labelled. Nothing is computed yet; run: python -m eval.checkpoint4_round3 score")
            return True
        _show(out, f"Item {ids.index(nxt['id']) + 1} of {len(items)}   ({len(got)} labelled)", nxt)
        a = _ask(inp, out, undo_ok=bool(cur))
        if a == "q":
            out("Progress saved. Run the same command to resume.")
            return False
        if a == "z":
            _append(log_path, {"undo": True})
            out("Last answer undone; it will be shown again.")
            continue
        note = inp("Optional note (Enter to skip) > ").strip()
        _append(log_path, {"id": nxt["id"], "label": KEYS[a], "note": note})


def run_label_command(inp=input, out=print) -> int:
    if not ITEMS.exists():
        out("Nothing built yet: run  python -m eval.checkpoint4_round3 build")
        return 1
    if not run_practice(json.loads(PRACTICE.read_text()), PRACTICE_LOG, inp, out):
        return 0
    run_label(json.loads(ITEMS.read_text()), LABEL_LOG, inp, out)
    return 0


def run_score() -> int:
    items = json.loads(ITEMS.read_text())
    labels = {a["id"]: a["label"] for a in labelled(_read_log(LABEL_LOG))}
    missing = [it["id"] for it in items if it["id"] not in labels]
    if missing:
        print(f"{len(missing)} of {len(items)} items are not labelled yet: nothing computed")
        return 1
    res = score_core(json.loads(KEY.read_text())["items"], labels)
    (DIR / "agreement.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "label", "score"])
    a = ap.parse_args(argv)
    return {"build": build_files, "label": run_label_command, "score": run_score}[a.cmd]()


if __name__ == "__main__":
    raise SystemExit(main())
