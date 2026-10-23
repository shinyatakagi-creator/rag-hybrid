"""python -m eval.build_question_kit  ->  eval/question_kit.md   (deterministic, seeded; no API calls, no Elasticsearch)

A kit for writing golden-set questions by hand:
  A) 12 exact-term candidates     rare terms (flags, field names, annotation keys, event reasons, error strings) in 1-5 docs
  B) 10 mixed candidates          the same kind of term plus one fact about it that is not just its name
  C) 12 conceptual passages       from different pages, each with its 5 rarest words (to avoid when writing the question)
  D) 4 unanswerable candidates    real facts that live only in the excluded folders, plus 2 off-topic questions

Everything is computed from the indexed chunk files, eval/doc_ids.tsv and the excluded source pages; every claim in the
kit (doc counts, absence of an answer string) is checked while building and the build fails if one does not hold.
"""
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from eval.docids import read_list
from eval.overlap import STOPWORDS, detect_exact_terms, stem
from eval.term_stats import load_chunks, report, term_stats

SEED = 11
OUT = "eval/question_kit.md"
CORPUS = Path("data/k8s/docs")
# generated listings: poor material for "what does this mean" excerpts and conceptual passages
GENERATED = ("reference/config-api/", "reference/instrumentation/metrics", "reference/labels-annotations-taints", "reference/kubelet-api/",
             "reference/using-api/deprecation-guide")
DEMO_TERMS = {"--max-requests-inflight", "--etcd-compaction-interval"}  # used in earlier demos; not offered again
QUOTA_A = {"flag": 3, "field": 3, "annotation": 2, "reason": 2, "error": 2}
QUOTA_B = {"flag": 3, "field": 4, "annotation": 2, "reason": 1}  # error strings live in code blocks: there is no prose fact about them
MAX_DOCS_PER_PAGE = 2  # across A and B together
CUE = re.compile(r"\b(default|defaults|by default|when|if|only|must|cannot|can't|will|unless|requires?|ignored|ignores|disabled|enabled|instead|otherwise|"
                 r"at most|at least|no longer|deprecated|allowed|not supported|takes effect|overrides?|overridden)\b", re.I)

_FLAG = re.compile(r"(?<![\w-])(--[a-z][a-z0-9]*(?:-[a-z0-9]+)+)(?![\w-])")
_ANNOT = re.compile(r"(?<![\w./-])((?:[a-z0-9][a-z0-9-]*\.)+[a-z]{2,}/[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9])(?![\w/-])")
_FIELD = re.compile(r"`([a-z]+(?:[A-Z][a-z0-9]+)+)`")
_PASCAL = re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b")
# error output a user actually sees: only lines inside code blocks, starting like a real message
_ERRLINE = re.compile(r"^\s*(?:\$\s*)?((?:Error from server|Error:|error:|Unable to connect|Unable to |The connection to the server|Failed to |failed to |"
                      r"no matches for kind|panic:|fatal:|Back-off|Warning\s+\w+)[^\n]{10,140})$")
_EVENT = re.compile(r"(?:^|\s)(?:Normal|Warning)\s+([A-Z][A-Za-z]{3,})\b")
_REASON_KV = re.compile(r"""(?i)\breason"?\s*[:=]\s*["'`]?([A-Z][A-Za-z]{3,})\b""")
_OFFICIAL = re.compile(r"(?:kubernetes\.io|k8s\.io)/")
_API_VERSION = re.compile(r"^v\d+((alpha|beta)\d+)?$")
_FENCE = re.compile(r"^[ \t]*(```|~~~)[^\n]*\n.*?^[ \t]*\1[ \t]*$", re.S | re.M)


def is_generated(doc_id: str) -> bool:
    return doc_id.startswith(GENERATED)


# -- candidate extraction ---------------------------------------------------------------------------------------
def error_prefix(line: str) -> str | None:
    """The longest literal fragment of an error line: split at quoted values, placeholders, '(x3 over 20s)' ages and column gaps,
    so what remains is the message text a user would search for."""
    frags = re.split(r"""\"|<|\{|%|\$|\[|\s{2,}|\(x\d+[^)]*\)""", line)
    best = max((f.strip().strip(":,.;-").strip() for f in frags), key=len, default="")
    if ">" in best or re.search(r"\d{3,}", best):  # leftover placeholder, or a pid / size / timestamp that changes per run
        return None
    return best if len(best) >= 18 and " " in best else None


def extract_candidates(chunks: list[dict]) -> dict[str, set[str]]:
    """kind -> set of candidate terms found in the chunk text."""
    out: dict[str, set[str]] = defaultdict(set)
    for c in chunks:
        t = c["content"]
        out["flag"].update(_FLAG.findall(t))
        out["field"].update(_FIELD.findall(t))
        for m in _ANNOT.finditer(t):
            k = m.group(1)
            domain, name = k.split("/", 1)
            if (re.match(r"v\d", name) or k.startswith(("github.com", "golang.org", "registry.k8s.io")) or "example" in k
                    or domain == "k8s.io" or domain.endswith("sigs.k8s.io")):
                continue  # apiVersion / group-version-kind references, Go module paths and docs placeholders are not annotation keys
            near = t[max(0, m.start() - 150): m.end() + 150].lower()  # a real key: an official domain, or called an annotation nearby
            if _OFFICIAL.search(k + "/") or "annotation" in near:
                out["annotation"].add(k)
        out["reason"].update(_EVENT.findall(t))
        out["reason"].update(_REASON_KV.findall(t))
        for line, is_code in prose_lines(t):
            m = _ERRLINE.match(line) if is_code else None
            p = error_prefix(m.group(1)) if m else None
            if p:
                out["error"].add(p)
    return out


class Index:
    """Page texts per chunker, doc sets per term, and the chunks of each page."""

    def __init__(self, chunks_dir: str = "data/chunks"):
        self.by_name = load_chunks(chunks_dir)
        self.pt = {n: self._join(cs) for n, cs in self.by_name.items()}
        self.doc_rows = {r["doc_id"]: r for r in read_list()}
        self.chunks_of: dict[str, list[dict]] = defaultdict(list)
        for c in self.by_name["heading"]:
            self.chunks_of[c["doc_id"]].append(c)
        self._cache: dict[str, tuple[list[str], list[str]]] = {}

    @staticmethod
    def _join(cs: list[dict]) -> dict[str, str]:
        d: dict[str, list[str]] = defaultdict(list)
        for c in cs:
            d[c["doc_id"]].append(c["content"])
        return {k: "\n".join(v) for k, v in d.items()}

    def docs(self, term: str) -> tuple[list[str], list[str]]:
        """(docs containing the term with the heading chunker, with the fixed chunker): case-sensitive substring."""
        if term not in self._cache:
            self._cache[term] = tuple(sorted(d for d, t in self.pt[n].items() if term in t) for n in ("heading", "fixed"))
        return self._cache[term]

    def in_range(self, term: str, lo: int = 1, hi: int = 5) -> bool:
        h, f = self.docs(term)
        return lo <= len(h) <= hi and lo <= len(f) <= hi


# -- excerpts, facts, rare words -----------------------------------------------------------------------------------
def prose_lines(content: str) -> list[tuple[str, bool]]:
    """[(line, is_code)] for each line of a chunk, marking lines inside fenced blocks."""
    flags, out = set(), []
    for m in _FENCE.finditer(content):
        flags.update(range(content.count("\n", 0, m.start()), content.count("\n", 0, m.end()) + 1))
    for i, line in enumerate(content.split("\n")):
        out.append((line, i in flags))
    return out


def standalone(text: str, term: str) -> bool:
    """The term occurs as a whole token, not inside a longer name (`kubeReserved` inside `kubeReservedCgroup`)."""
    return re.search(r"(?<![\w-])" + re.escape(term) + r"(?![\w-])", text) is not None


def best_chunk(idx: Index, term: str, docs: list[str], kind: str = "") -> tuple[str, dict] | None:
    """The chunk where the term is best explained: prose lines containing it, little code, a sensible size.
    Error strings only ever occur in code blocks, so for them a code line counts."""
    best, best_score = None, -1e9
    for d in docs:
        if is_generated(d):
            continue
        for c in idx.chunks_of[d]:
            if term not in c["content"]:
                continue
            lines = prose_lines(c["content"])
            n_prose = sum(1 for l, code in lines if standalone(l, term) and (kind == "error" or not code))
            code_share = sum(1 for _, code in lines if code) / max(len(lines), 1)
            score = 3 * n_prose - 4 * code_share + (1 if 80 <= c["token_count"] <= 400 else 0) + (1 if term in "\n".join(l for l, _ in lines[:5]) else 0)
            if n_prose and score > best_score:
                best, best_score = (d, c), score
    return best


def cut_at_word(line: str, width: int) -> str:
    if len(line) <= width:
        return line
    return line[:width].rsplit(" ", 1)[0] + " …"


def excerpt(content: str, term: str, kind: str = "", lo: int = 3, hi: int = 6, width: int = 260) -> str | None:
    """3-6 lines around the first prose occurrence of the term, with at least one explanatory prose line.
    For an error string (which lives in a code block) the 3 lines before the block and the whole block are shown, up to 9 lines.
    An excerpt never starts inside a code block and never ends with a fence that opens and does not close."""
    lines = prose_lines(content)  # [(line, is_code)]
    if kind == "error":
        pos = next((i for i, (l, _) in enumerate(lines) if term in l), None)
        if pos is None:
            return None
        s, e = pos, pos
        while s > 0 and lines[s - 1][1]:
            s -= 1
        while e + 1 < len(lines) and lines[e + 1][1]:
            e += 1
        fence = lambda l: l.lstrip().startswith(("```", "~~~"))
        inner = [l for l, _ in lines[s: e + 1] if not fence(l)]
        j = next(i for i, l in enumerate(inner) if term in l)
        lead = [(l, False) for l, _ in lines[max(0, s - 3): s] if l.strip()][-2:]  # the prose that introduces the output
        win = lead + [("```", True)] + [(l, True) for l in inner[j: j + 2]] + [("```", True)]  # error line + the next one, in a balanced fence
    else:
        pos = next((i for i, (l, code) in enumerate(lines) if standalone(l, term) and not code), None)
        if pos is None:
            return None
        start = max(0, pos - 1)
        win = lines[start:start + hi]
        while win and win[0][1]:  # the window began inside a code block: skip to the first prose line
            win = win[1:]
    marks = [i for i, (l, _) in enumerate(win) if l.lstrip().startswith(("```", "~~~"))]
    if len(marks) % 2:
        win = win[: marks[-1]]
    while win and not win[0][0].strip():
        win = win[1:]
    while win and not win[-1][0].strip():
        win = win[:-1]
    if len([l for l, _ in win if l.strip()]) < lo or not any(len(l.strip()) >= 30 and not code for l, code in win):
        return None
    return "\n".join(cut_at_word(l.rstrip(), width) for l, _ in win)


def only_in_command_example(sentence: str, term: str) -> bool:
    """True when every whole-token occurrence of the term sits inside a backticked span that contains a space (`kompose convert --x`)."""
    outside = re.sub(r"`[^`]*\s[^`]*`", " ", sentence)
    return not standalone(outside, term)


MIN_FACT_WORDS = 6  # shorter than this is a label or a bare identifier, not a statement about the term


def extract_fact(content: str, term: str) -> str | None:
    """One sentence about the term that says something other than its name: a default, condition, behaviour or consequence."""
    prose = "\n".join(l if not code else "" for l, code in prose_lines(content))  # code blocks are not facts
    paras = [p for p in re.split(r"\n\s*\n", prose) if p.strip() and not p.lstrip().startswith("|")]
    best, best_score = None, 0
    for p in paras:
        text = re.sub(r"\s+", " ", p).strip()
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z`*\-\[])", text):
            s = re.sub(r"^[*\-]\s+", "", s).strip()
            if not 40 <= len(s) <= 320 or not standalone(s, term) or only_in_command_example(s, term):
                continue  # the sentence itself must mention the term, as a whole token, and not just inside a command line
            cues = len(CUE.findall(s))
            if cues and cues > best_score and len(s.split()) >= MIN_FACT_WORDS:
                best, best_score = re.sub(r"\s+\d+\.$", "", s), cues  # a trailing list marker ("... argument. 1.") is not part of the sentence
    return best


_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]{2,27}")


def token_frequency(texts: list[str]) -> Counter:
    """Pages containing each whole token (lowercased, lightly stemmed), the way a search engine tokenises: camelCase is NOT
    split, so `GenericWorkload` is one rare token, not 'generic' + 'workload'."""
    df: Counter = Counter()
    for t in texts:
        df.update({stem(w.lower()) for w in _TOKEN.findall(t)})
    return df


def rarest_words(text: str, tokdf: Counter, k: int = 5) -> list[tuple[str, int]]:
    """The k tokens of `text` found on the fewest pages (4+ letters, no stopwords, must contain a vowel), as (as written, pages)."""
    seen: dict[str, tuple[str, int]] = {}
    for w in _TOKEN.findall(text):
        lw = w.lower()
        if len(w) < 4 or lw in STOPWORDS or not re.search("[aeiou]", lw):
            continue
        s = stem(lw)
        seen.setdefault(s, (w, max(tokdf[s], 1)))
    return sorted(seen.values(), key=lambda x: (x[1], -len(x[0]), x[0].lower()))[:k]


# -- building the sections -------------------------------------------------------------------------------------------
def excluded_terms(drafts_path: str = "eval/golden_drafts.jsonl") -> set[str]:
    """Terms used by drafts d023-d038 (declared exact terms and any identifier in their questions) plus the demo terms."""
    out = set(DEMO_TERMS)
    for line in open(drafts_path, encoding="utf8"):
        d = json.loads(line)
        if d["id"] >= "d023":
            out.add(d["exact_term"].strip("`"))
            out.update(t.strip("`") for t in detect_exact_terms(d["question"]))
    return {t.lower() for t in out if t}


def clashes(term: str, banned: set[str]) -> bool:
    t = term.lower()
    return any(t == b or t in b or b in t for b in banned)


def pick_terms(idx: Index, cands: dict[str, set[str]], quota: dict[str, int], banned: set[str], used_docs: dict[str, int],
               taken: set[str], need_fact: bool, rng: random.Random) -> tuple[list[dict], dict[str, int]]:
    picked, pool_sizes = [], {}
    for kind, n in quota.items():
        pool = sorted(t for t in cands.get(kind, ()) if 5 <= len(t) <= 70 and t not in taken and idx.in_range(t) and not clashes(t, banned))
        pool_sizes[kind] = len(pool)
        rng.shuffle(pool)
        got = 0
        for t in pool:
            if got == n:
                break
            h, f = idx.docs(t)
            if any(used_docs[d] >= MAX_DOCS_PER_PAGE for d in h):
                continue
            bc = best_chunk(idx, t, h, kind)
            if not bc:
                continue
            doc, chunk = bc
            ex = excerpt(chunk["content"], t, kind)
            fact = extract_fact(chunk["content"], t) if need_fact else None
            if ex is None or (need_fact and not fact):
                continue
            for d in h:
                used_docs[d] += 1
            taken.add(t)
            picked.append({"term": t, "kind": kind, "docs": h, "docs_fixed": f, "best_doc": doc, "chunk": chunk, "excerpt": ex, "fact": fact})
            got += 1
    return picked, pool_sizes


_META = re.compile(r"^(Feature state|Feature gate):", re.I)
_BLOB = re.compile(r"(?<![(/\w.-])[A-Za-z0-9+/=_]{30,}(?![\w/-])")  # base64 / hash-like runs make a poor passage
_LINK_ITEM = re.compile(r"^\s*[*\-]\s*\[")


def passage_lines(content: str) -> list[str]:
    """Prose lines of a chunk without metadata lines such as 'Feature state: ...' (blank lines dropped)."""
    return [l.rstrip() for l, code in prose_lines(content) if l.strip() and not code and not _META.match(l.strip())]


def pick_passages(idx: Index, tokdf: Counter, avoid_docs: set[str], rng: random.Random) -> list[dict]:
    quota = {"concepts": 5, "tasks": 4, "reference": 3}
    pool = [c for c in idx.by_name["heading"]
            if 150 <= c["token_count"] <= 450 and not is_generated(c["doc_id"]) and c["doc_id"] not in avoid_docs and c["doc_id"] in idx.doc_rows
            and c["doc_id"].split("/")[0] in quota and c["doc_id"] != "reference/_index"]
    good = []
    for c in sorted(pool, key=lambda c: c["chunk_id"]):
        lines = prose_lines(c["content"])
        code = sum(1 for _, k in lines if k) / max(len(lines), 1)
        table = sum(1 for l, _ in lines if l.lstrip().startswith("|")) / max(len(lines), 1)
        text = passage_lines(c["content"])
        links = sum(1 for l in text if _LINK_ITEM.match(l)) / max(len(text), 1)
        if (code <= 0.15 and table <= 0.05 and links <= 0.2 and len(text) >= 5 and not _BLOB.search(c["content"])
                and not c["heading_path"].lower().endswith(("what's next", "before you begin"))):
            good.append(c)
    rng.shuffle(good)
    got: list[dict] = []
    per, used = dict.fromkeys(quota, 0), set()
    for c in good:
        f = c["doc_id"].split("/")[0]
        if per[f] >= quota[f] or c["doc_id"] in used:
            continue
        take = passage_lines(c["content"])[:10]
        if len(take) < 5:
            continue
        ex = "\n".join(cut_at_word(l, 260) for l in take)
        got.append({"chunk": c, "excerpt": ex, "rare": rarest_words(ex, tokdf)})  # rare words come from the text shown, not the whole chunk
        per[f] += 1
        used.add(c["doc_id"])
    return got


# -- D: unanswerable candidates (curated; every claim is verified) -------------------------------------------------------------
UNANSWERABLE = [
    {"folder": "command-line-tools-reference", "source": "reference/command-line-tools-reference/kube-controller-manager.md", "name": "--terminated-pod-gc-threshold",
     "answer": "12500", "question": "What is the default value of the kube-controller-manager --terminated-pod-gc-threshold flag?"},
    {"folder": "command-line-tools-reference", "source": "reference/command-line-tools-reference/kube-proxy.md", "name": "--conntrack-min",
     "answer": "131072", "question": "What is the default minimum number of conntrack entries that kube-proxy allocates, as set by --conntrack-min?"},
    {"folder": "kubectl", "source": "reference/kubectl/generated/kubectl_attach/_index.md", "name": "--detach-keys",
     "answer": "ctrl-p,ctrl-q", "question": "Which key sequence does kubectl attach use by default to detach from a container?"},
    {"folder": "kubernetes-api", "source": "reference/kubernetes-api/core/pod-v1.md", "name": "keyring is the path to key ring for RBDUser",
     "label": "RBD volume source: keyring", "name_check": "RBDUser", "answer": "/etc/ceph/keyring",
     "question": "What is the default path of the keyring file for an RBD volume in a Pod spec?"},
]
OFF_TOPIC = [("How do I bake a loaf of sourdough bread at home?", "sourdough"), ("How many moons does Jupiter have?", "Jupiter")]


def source_fact(item: dict) -> str:
    """The fact as the excluded source page states it (HTML and shortcodes removed), found by flag/field name and answer string."""
    text = (CORPUS / item["source"]).read_text(encoding="utf8")
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>|\{\{.*?\}\}|&nbsp;", " ", text))
    i = plain.find(item["name"])
    while i != -1:
        window = plain[i: i + 520]
        if item["answer"] in window:
            end = window.find(item["answer"]) + len(item["answer"])
            tail = window[end:]
            stop = min([m.start() for m in re.finditer(r"\. |\s-{1,2}[a-z]|\s--", tail)] + [len(tail)])  # up to the end of the sentence / next flag
            return (window[:end] + tail[: stop + 1]).strip()
        i = plain.find(item["name"], i + 1)
    raise ValueError(f"{item['source']}: {item['name']} and {item['answer']!r} not found together")


def verify_unanswerable(idx: Index, item: dict) -> dict:
    ans = term_stats(item["answer"], idx.by_name)
    if any(s["chunks"] for s in ans.values()):
        raise ValueError(f"answer string {item['answer']!r} IS in the index: {report(item['answer'], ans)}")
    chk = item.get("name_check", item["name"])
    return {"fact": source_fact(item), "answer_report": report(item["answer"], ans), "name_report": report(chk, term_stats(chk, idx.by_name))}


# -- assembling the markdown -----------------------------------------------------------------------------------------------
def url_of(idx: Index, doc: str) -> str:
    return idx.doc_rows[doc]["url"]


def stats_line(idx: Index, term: str) -> str:
    s = term_stats(term, idx.by_name, case=True)
    return " | ".join(f"{n}: {s[n]['chunks']} chunks in {s[n]['docs']} docs" for n in ("fixed", "heading"))


def render_terms(idx: Index, items: list[dict], prefix: str, with_fact: bool) -> list[str]:
    out = []
    for i, it in enumerate(items, 1):
        c = it["chunk"]
        out += [f"### {prefix}{i}. `{it['term']}` · {it['kind']}", "",
                f"- **Docs containing it ({len(it['docs'])}):** " + ", ".join(f"`{d}`" for d in it["docs"]),
                f"- **term_stats (case-sensitive):** {stats_line(idx, it['term'])}",
                f"- **Best page:** `{it['best_doc']}` · {idx.doc_rows[it['best_doc']]['title']} · {url_of(idx, it['best_doc'])}",
                f"- **Section:** {c['heading_path']}"]
        if with_fact:
            out.append(f"- **Fact about it (verbatim from the page):** {it['fact']}")
        out += ["", "````text", it["excerpt"], "````", ""]  # 4 backticks: an excerpt may contain its own ``` fences
    return out


def build(idx: Index | None = None) -> tuple[str, dict]:
    idx = idx or Index()
    rng = random.Random(SEED)
    banned = excluded_terms()
    all_chunks = idx.by_name["heading"] + idx.by_name["fixed"]
    cands = extract_candidates(all_chunks)
    used_docs: dict[str, int] = defaultdict(int)
    taken: set[str] = set()
    A, pool_a = pick_terms(idx, cands, QUOTA_A, banned, used_docs, taken, False, rng)
    B, pool_b = pick_terms(idx, cands, QUOTA_B, banned, used_docs, taken, True, rng)
    if len(B) < sum(QUOTA_B.values()):  # a quota category ran short: top up with any other kind that has a prose fact
        extra, _ = pick_terms(idx, cands, {k: sum(QUOTA_B.values()) - len(B) for k in ("field", "flag", "annotation")}, banned, used_docs, taken, True, rng)
        B += extra[: sum(QUOTA_B.values()) - len(B)]
    texts = {d: idx.pt["heading"][d] for d in idx.pt["heading"]}
    tokdf, n_docs = token_frequency(list(texts.values())), len(texts)
    drafts = {json.loads(l)["source_doc_id"] for l in open("eval/golden_drafts.jsonl", encoding="utf8")}
    avoid = drafts | {d for it in A + B for d in it["docs"]}
    C = pick_passages(idx, tokdf, avoid, rng)
    D = [{**u, **verify_unanswerable(idx, u)} for u in UNANSWERABLE]
    off = [(q, report(w, term_stats(w, idx.by_name))) for q, w in OFF_TOPIC]
    for q, rep in off:
        if "chunks=   0" not in rep.split("\n")[1]:
            raise ValueError(f"off-topic question {q!r} has indexed matches")

    L = ["# Question kit for the golden set", "",
         "Generated by `python -m eval.build_question_kit` (seed %d; no API calls). Every `doc_id` below is in `eval/doc_ids.tsv` and has chunks. " % SEED +
         "Numbers come from `eval.term_stats` on the indexed chunk files; `case-sensitive` means exact-case substring matching. "
         "The kit is raw material: write your own questions, choose your own `expected_doc_ids`, then run `python -m eval.golden_check` and `python -m eval.overlap_check`.", "",
         f"Terms already used in drafts d023-d038 (and the demo flags) are excluded: {', '.join(sorted(banned))}. "
         f"Candidate pools before picking (terms in 1-5 docs, not excluded): A {pool_a}, B {pool_b}. No page supplies more than {MAX_DOCS_PER_PAGE} terms across A and B.", ""]
    L += ["## A) Exact-term candidates (12)", "", "Each term appears in 1-5 docs, so a question that contains it should point to a small set of pages.", ""]
    L += render_terms(idx, A, "A", False)
    L += ["## B) Mixed candidates (10)", "", "Different rare terms from A, each with one fact on the page about the term that is not just its name. "
          "A mixed question joins the term to that behaviour in everyday words.", ""]
    L += render_terms(idx, B, "B", True)
    L += ["## C) Conceptual passages (12)", "",
          "From 12 different pages (not config/metric listings, not the source pages of the drafts, not the pages used in A/B). "
          "`Rarest words` are the 5 tokens of the excerpt found on the fewest pages (page count out of %d), counted the way a search engine "
          "tokenises (camelCase stays one token, light stemming); avoid them, and the page title's words, in your question." % n_docs, ""]
    for i, p in enumerate(C, 1):
        c = p["chunk"]
        L += [f"### C{i}. `{c['doc_id']}`", "", f"- **Title:** {idx.doc_rows[c['doc_id']]['title']} · {url_of(idx, c['doc_id'])}", f"- **Section:** {c['heading_path']}",
              "- **Rarest words (avoid):** " + ", ".join(f"{w} ({n})" for w, n in p["rare"]), "", "````text", p["excerpt"], "````", ""]
    L += ["## D) Unanswerable candidates", "",
          "Real Kubernetes facts that live only in the excluded folders. `Answer string` appears in 0 indexed chunks (proof below, from `eval.term_stats`). "
          "The name of the flag or field may still be mentioned in indexed pages without its default, so these are *near-corpus* unanswerables, harder than off-topic ones. "
          "A model that knows Kubernetes may know the answer: the test is whether the system refuses or answers from memory.", ""]
    for i, d in enumerate(D, 1):
        L += [f"### D{i}. {d.get('label', d['name'])} · excluded folder `{d['folder']}`", "", f"- **Source page (not indexed):** `{d['source']}`",
              f"- **Fact as the source states it:** {d['fact']}", f"- **Answer string:** `{d['answer']}`", f"- **Question idea:** {d['question']}", "",
              "```text", d["answer_report"], "", d["name_report"], "```", ""]
    L += ["### Two clearly off-topic questions", ""]
    for q, rep in off:
        L += [f"- {q}", "", "```text", rep, "```", ""]
    data = {"A": A, "B": B, "C": C, "D": D, "banned": sorted(banned), "pool_a": pool_a, "pool_b": pool_b}
    return "\n".join(L), data


def main() -> None:
    md, data = build()
    Path(OUT).write_text(md, encoding="utf8")
    print(f"wrote {OUT}: A={len(data['A'])} B={len(data['B'])} C={len(data['C'])} D={len(data['D'])}  pools A={data['pool_a']} B={data['pool_b']}")


if __name__ == "__main__":
    main()
