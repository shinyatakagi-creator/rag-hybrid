"""Kubernetes docs markdown -> cleaned Doc records (front matter, Hugo shortcodes, includes resolved)."""
import html
import html.entities
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

SECTIONS = ("concepts", "tasks", "reference")
# Scope B (see data/CORPUS.md): generated / stub-heavy reference dirs are skipped.
EXCLUDE = (
    "reference/kubernetes-api",
    "reference/glossary",
    "reference/command-line-tools-reference",
    "reference/setup-tools",
    "reference/kubectl",
)
BOILERPLATE_INCLUDES = {"task-tutorial-prereqs.md"}  # 121 pages; identical text would skew BM25
HEADING_I18N = {
    "whatsnext": "What's next",
    "prerequisites": "Before you begin",
    "cleanup": "Cleaning up",
    "objectives": "Objectives",
    "seealso": "See also",
}

# closing --- may be the last bytes of the file (4 section _index pages end without a newline)
_FM = re.compile(r"\A---\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)
_ATTR = re.compile(r'(\w+)="([^"]*)"')
def _sc(inner: str) -> str:
    return r"\{\{[<%]\s*" + inner + r"\s*[>%]\}\}"
# A fenced block may be indented (list items: 1,456 of the 8,158 fence lines in the corpus) and may be left unclosed.
_FENCE_RE = re.compile(r"^[ \t]*(```|~~~)[^\n]*(?:\n.*?(?:^[ \t]*\1[`~]*[ \t]*$|\Z)|\Z)", re.S | re.M)
_INLINE_CODE_RE = re.compile(r"(`+)(?!`)[^\n]*?(?<!`)\1(?!`)")  # `x` or ``x`` on one line
_ENTITY_RE = re.compile(r"&(?:#\d+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]{1,31});")


def split_code(text: str, pattern: re.Pattern = _FENCE_RE) -> list[tuple[str, bool]]:
    """Cut text into [(segment, is_code)] on `pattern` matches (fenced blocks by default); segments concatenate back to text."""
    out, pos = [], 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            out.append((text[pos : m.start()], False))
        out.append((m.group(0), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return out


def _decode_one(entity: str) -> str | None:
    """The character for one `&...;` token, or None if it is not a real entity. Named entities are looked up exactly in the
    HTML5 table: html.unescape alone would turn the made-up `&notanentity;` into `¬anentity;` (legacy `&not` prefix)."""
    if entity[1] == "#":
        return html.unescape(entity) if html.unescape(entity) != entity else None
    return html.entities.html5.get(entity[1:])


def count_entities(text: str) -> int:
    return sum(1 for m in _ENTITY_RE.finditer(text) if _decode_one(m.group(0)) is not None)


def decode_entities(text: str) -> tuple[str, int]:
    """Decode every real entity in `text` (html.unescape semantics, exact names only); a non-breaking space becomes a plain
    space. Returns (text, how many were decoded)."""
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        d = _decode_one(m.group(0))
        if d is None:
            return m.group(0)
        n += 1
        return d.replace("\xa0", " ")

    return _ENTITY_RE.sub(sub, text), n


@dataclass
class Doc:
    doc_id: str
    url: str
    title: str
    text: str


class Cleaner:
    """Resolves shortcodes against the corpus root (the dir holding docs/, examples/, includes/)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.unknown: Counter = Counter()
        self.whats_next_removed: list[str] = []
        self.entities_decoded = 0  # HTML entities turned into characters (prose only)
        self.entities_left_in_code = 0  # entities inside fenced code or inline code spans, deliberately untouched
        self.missing: list[str] = []
        self.glossary = self._load_glossary()

    def _load_glossary(self) -> dict:
        out = {}
        for p in (self.root / "docs/reference/glossary").glob("*.md"):
            t = p.read_text(encoding="utf8")
            m = _FM.match(t)
            if not m:
                continue
            fm = m.group(1)
            tid = re.search(r"^id:\s*(\S+)", fm, re.M)
            short = re.search(r"^short_description:\s*>?\s*\n?\s*(.+?)\n(?:\w|\Z)", fm + "\nx", re.M | re.S)
            if tid:
                body = t[m.end():].split("<!--more-->")[0].strip()
                out[tid.group(1)] = (" ".join(short.group(1).split()) if short else "", body)
        return out

    # -- helpers ---------------------------------------------------------
    def _read(self, path: Path) -> str | None:
        if path.is_file():
            return path.read_text(encoding="utf8")
        self.missing.append(str(path))
        return None

    def _include(self, name: str, page_dir: Path, depth: int) -> str:
        if name in BOILERPLATE_INCLUDES:
            return ""
        for base in (self.root / "includes", page_dir):
            if (base / name).is_file():
                t = (base / name).read_text(encoding="utf8")
                m = _FM.match(t)
                return self.clean(t[m.end():] if m else t, page_dir, depth + 1)
        self.missing.append(f"include:{name}")
        return ""

    def _code_sample(self, attrs: dict) -> str:
        f = attrs.get("file", "").lstrip("/")
        code = self._read(self.root / "examples" / f)
        if code is None:
            return ""
        lang = attrs.get("language") or Path(f).suffix.lstrip(".") or ""
        return f"```{lang}\n{code.rstrip()}\n```"

    def _glossary_def(self, attrs: dict) -> str:
        short, body = self.glossary.get(attrs.get("term_id", ""), ("", ""))
        text = body if attrs.get("length") == "all" else short
        return self.clean(f"{attrs.get('prepend', '')} {text}".strip(), self.root, 3)

    # -- main ------------------------------------------------------------
    def clean(self, text: str, page_dir: Path, depth: int = 0) -> str:
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        text = re.sub(_sc("comment") + r".*?" + _sc(r"/\s*comment"), "", text, flags=re.S)
        text = re.sub(r"^(?=\{\{[<%]\s*heading\b)", "## ", text, flags=re.M)  # bare heading shortcode -> H2

        text = re.sub(_sc(r"highlight[^>%]*hl_inline=true[^>%]*") + r"(.*?)" + _sc(r"/\s*highlight"), r"`\1`", text, flags=re.S)

        def sc(m: re.Match) -> str:
            name, args = m.group(1), m.group(2)
            attrs = dict(_ATTR.findall(args))
            pos = re.match(r'\s*"([^"]*)"', args)
            if name == "include":
                return self._include(pos.group(1), page_dir, depth) if pos and depth < 3 else ""
            if name == "code_sample":
                return self._code_sample(attrs)
            if name in ("ref", "relref"):
                return pos.group(1) if pos else ""
            if name == "glossary_tooltip":
                return attrs.get("text") or attrs.get("term_id", "").replace("-", " ")
            if name == "glossary_definition":
                return self._glossary_def(attrs)
            if name == "heading":  # Hugo pages write `## {{% heading "x" %}}`; the hashes are already there
                return HEADING_I18N.get(pos.group(1), pos.group(1)) if pos else ""
            if name == "feature-state":
                if "feature_gate_name" in attrs:
                    return f"Feature gate: {attrs['feature_gate_name']}"
                bits = [f"Kubernetes {attrs['for_k8s_version']}"] if "for_k8s_version" in attrs else []
                return "Feature state: " + " ".join(bits + [f"[{attrs['state']}]"] if "state" in attrs else bits)
            if name in ("note", "caution", "warning"):
                return name.capitalize() + ":"
            if name == "tab":
                return f"**{attrs.get('name', '')}**"
            if name == "details":
                return f"**{attrs.get('summary', '')}**"
            if name == "table":
                return f"Table: {attrs['caption']}" if "caption" in attrs else ""
            if name == "figure":
                return f"Figure: {attrs.get('title') or attrs.get('caption') or attrs.get('alt', '')}".strip()
            if name == "alert":
                return attrs.get("text", "")
            if name in ("highlight", "mermaid"):
                lang = "mermaid" if name == "mermaid" else args.split()[0] if args.split() else ""
                return f"```{lang}"
            if name in ("tabs", "skew", "param", "version-check", "thirdparty-content"):
                return ""
            self.unknown[name] += 1
            return ""

        text = re.sub(r"\{\{[<%]\s*([a-zA-Z_-]+)([^>%]*?)\s*[>%]\}\}", sc, text)
        # closing tags: highlight/mermaid end a fence, everything else disappears
        text = re.sub(_sc(r"/\s*(?:highlight|mermaid)"), "```", text)  # `{{</ mermaid >}}` has a space after the slash
        text = re.sub(r"\{\{[<%]\s*/\s*[a-zA-Z_-]+\s*[>%]\}\}", "", text)
        return self._strip_html(text, decode=(depth == 0))

    def _strip_html(self, text: str, decode: bool = False) -> str:
        """Drop layout HTML outside code fences, keeping the text. With decode=True (the final, top-level pass only,
        so nothing is decoded twice) also html.unescape entities outside fenced blocks AND inline code spans, last of
        all so a decoded `&lt;div&gt;` is not mistaken for a tag. Entities left in code are counted, not changed."""
        out = []
        for seg, is_fence in split_code(text):
            if is_fence:
                if decode:
                    self.entities_left_in_code += count_entities(seg)
                out.append(seg)
                continue
            seg = re.sub(r"</?code>", "`", seg, flags=re.I)
            seg = re.sub(r"<br\s*/?>|</br>|</(?:p|tr|li|div|table|thead|tbody)>", "\n", seg, flags=re.I)
            # case-insensitive: the generated config-API pages use <B>[Required]</B> (1,498 tags in 294 chunks before this)
            seg = re.sub(r"</?(?:span|div|label|td|th|tr|table|thead|tbody|p|ul|ol|li|a|b|i|em|strong|pre|sup|sub|small|center|img|hr)(?:\s[^<>]*)?/?>", " ", seg, flags=re.I)
            if decode:
                pieces = []
                for sub, is_inline in split_code(seg, _INLINE_CODE_RE):
                    if is_inline:
                        self.entities_left_in_code += count_entities(sub)
                        pieces.append(sub)
                    else:
                        d, n = decode_entities(sub)
                        self.entities_decoded += n
                        pieces.append(d)
                seg = "".join(pieces)
            out.append(seg)
        return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+\n", "\n", "".join(out))).strip()


# CommonMark allows an ATX heading to be indented by up to 3 spaces (one page has ` ## What's next`)
_WHATS_NEXT = re.compile(r"^ {0,3}(#{1,6})[ \t]+what['’]s[ \t]+next[ \t]*(\{#[^}]*\})?[ \t]*$", re.I)
_ANY_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+\S")


def strip_whats_next(text: str) -> tuple[str, list[str]]:
    """Remove every "What's next" section (its heading up to the next heading of the same or higher level).

    Those sections are navigation links, not answer content. Fence-aware: a `## What's next` inside a code block is
    left alone. Returns the cleaned text and the removed sections (for counting)."""
    out, removed, cur, skip_level, fence = [], [], [], None, False
    for line in text.split("\n"):
        is_fence = line.lstrip().startswith(("```", "~~~"))
        if is_fence:
            fence = not fence
        elif not fence and (m := _ANY_HEADING.match(line)):
            level = len(m.group(1))
            if skip_level is not None and level <= skip_level:
                removed.append("\n".join(cur))
                skip_level = None
            if skip_level is None and _WHATS_NEXT.match(line):
                skip_level, cur = level, [line]
                continue
        (cur if skip_level is not None else out).append(line)
    if skip_level is not None:
        removed.append("\n".join(cur))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip(), removed


def in_scope(rel: Path) -> bool:
    s = rel.as_posix()
    return rel.suffix == ".md" and s.split("/")[0] in SECTIONS and not s.startswith(tuple(e + "/" for e in EXCLUDE))


def doc_id_and_url(rel: Path) -> tuple[str, str]:
    """rel is the path under docs/. _index pages keep `_index` in the doc_id; the URL is the directory."""
    doc_id = rel.with_suffix("").as_posix()
    url_path = rel.parent.as_posix() if rel.name == "_index.md" else doc_id
    return doc_id, f"https://kubernetes.io/docs/{url_path}/"


def is_headless(fm: str) -> bool:
    """Hugo include partials: not public pages (`headless: true`, or `_build: render: never`), so never indexed."""
    return bool(re.search(r"^headless:\s*true\s*$", fm, re.M) or re.search(r"^[ \t]+render:\s*never\s*$", fm, re.M))


def parse_title(fm: str, fallback: str) -> str:
    m = re.search(r"^title:\s*(.+)$", fm, re.M)
    return m.group(1).strip().strip("\"'") if m else fallback


def load_corpus(root: Path, cleaner: Cleaner | None = None, raw: bool = False) -> list[Doc]:
    """root = corpus dir containing docs/, examples/, includes/. raw=True skips shortcode cleanup (for token accounting)."""
    root = Path(root)
    cleaner = cleaner or Cleaner(root)
    docs_dir = root / "docs"
    docs = []
    for p in sorted(docs_dir.rglob("*.md")):
        rel = p.relative_to(docs_dir)
        if not in_scope(rel):
            continue
        t = p.read_text(encoding="utf8")
        m = _FM.match(t)
        fm, body = (m.group(1), t[m.end():]) if m else ("", t)
        if is_headless(fm):
            continue  # include partials are read by Cleaner._include, they are not documents
        doc_id, url = doc_id_and_url(rel)
        title = parse_title(fm, rel.parent.name if rel.name == "_index.md" else rel.stem)
        if raw:
            text = body.strip()
        else:  # before either chunker, so fixed and heading see the same text
            text, removed = strip_whats_next(cleaner.clean(body, p.parent))
            cleaner.whats_next_removed.extend(removed)
        docs.append(Doc(doc_id, url, title, text))
    return docs
