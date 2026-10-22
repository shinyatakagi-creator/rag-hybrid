"""Two chunkers over cleaned Docs: fixed-size (structure-blind) and heading-aware.

Token counts use cl100k_base (the text-embedding-3-small tokenizer) and are measured on the
text that gets embedded: heading_path + "\\n" + content. No embedded chunk may exceed MAX_TOKENS.
"""
import hashlib
import re

import tiktoken
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from .loaders import Doc

ENC = tiktoken.get_encoding("cl100k_base")
MAX_TOKENS = 800
FIXED_SIZE, FIXED_OVERLAP = 400, 50
HEADING_TARGET = 600
MIN_SECTION = 100  # sections below this many tokens are merged into the next one
MARGIN = 20  # slack for tokenisation differences when concatenating strings
_SEP_ROW = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


def ntok(s: str) -> int:
    return len(ENC.encode(s, disallowed_special=()))


def embed_text(c: dict) -> str:
    return f"{c['heading_path']}\n{c['content']}"


def make_chunk_id(doc_id: str, chunker: str, position: int, content: str) -> str:
    return hashlib.sha256(f"{doc_id}\x00{chunker}\x00{position}\x00{content}".encode()).hexdigest()[:16]


def _record(doc: Doc, chunker: str, position: int, heading_path: str, content: str) -> dict:
    c = {
        "chunk_id": make_chunk_id(doc.doc_id, chunker, position, content),
        "doc_id": doc.doc_id,
        "url": doc.url,
        "title": doc.title,
        "heading_path": heading_path,
        "content": content,
        "token_count": 0,
        "chunker": chunker,
        "position": position,
    }
    c["token_count"] = ntok(embed_text(c))
    return c


# -- fixed ------------------------------------------------------------------
def fixed_chunks(doc: Doc) -> list[dict]:
    sp = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base", chunk_size=FIXED_SIZE, chunk_overlap=FIXED_OVERLAP
    )
    # ponytail: fixed chunks get only the page title as heading_path (structure-blind by design)
    return [_record(doc, "fixed", i, doc.title, p) for i, p in enumerate(sp.split_text(doc.text))]


# -- heading-aware ------------------------------------------------------------
def _hard_split(text: str, budget: int) -> list[str]:
    ids = ENC.encode(text, disallowed_special=())
    return [ENC.decode(ids[i : i + budget]) for i in range(0, len(ids), budget)]


def _blocks(text: str) -> list[tuple[str, str]]:
    """Split markdown into ('fence'|'table'|'text', block) keeping fences and tables whole."""
    out, cur, kind, in_fence = [], [], "text", False

    def flush():
        nonlocal cur, kind
        if cur:
            out.append((kind, "\n".join(cur)))
        cur, kind = [], "text"

    for line in text.split("\n"):
        s = line.lstrip()
        if in_fence:
            cur.append(line)
            if s.startswith("```") or s.startswith("~~~"):
                in_fence = False
                flush()
        elif s.startswith("```") or s.startswith("~~~"):
            flush()
            cur, kind, in_fence = [line], "fence", True
        elif s.startswith("|"):
            if kind != "table":
                header = cur.pop() if kind == "text" and cur and "|" in cur[-1] and _SEP_ROW.match(line) else None
                flush()  # header row without a leading pipe belongs to the table, not the paragraph above
                kind = "table"
                cur = [header] if header else []
            cur.append(line)
        elif not s:
            flush()
        else:
            if kind == "table":
                flush()
            cur.append(line)
    flush()
    return out


def _pack_lines(head: list[str], lines: list[str], tail: list[str], budget: int) -> list[str]:
    """Greedy line packing; head/tail (fence markers or table header) repeat in every piece."""
    pieces, cur = [], []
    overhead = ntok("\n".join(head + tail))
    for line in lines:
        if overhead + ntok(line) > budget:  # single line too big: slice by tokens
            if cur:
                pieces.append(cur)
                cur = []
            pieces += [[part] for part in _hard_split(line, max(budget - overhead, 50))]
            continue
        if cur and ntok("\n".join(head + cur + [line] + tail)) > budget:
            pieces.append(cur)
            cur = []
        cur.append(line)
    if cur:
        pieces.append(cur)
    return ["\n".join(head + p + tail) for p in pieces]


def _split_block(kind: str, block: str, budget: int) -> list[str]:
    lines = block.split("\n")
    if kind == "fence":
        closed = len(lines) > 1 and lines[-1].lstrip().startswith(("```", "~~~"))
        return _pack_lines(lines[:1], lines[1:-1] if closed else lines[1:], lines[-1:] if closed else ["```"], budget)
    if kind == "table":
        n = 2 if len(lines) > 1 and _SEP_ROW.match(lines[1]) else 0
        return _pack_lines(lines[:n], lines[n:], [], budget)
    sp = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base", chunk_size=budget, chunk_overlap=FIXED_OVERLAP
    )
    return [q for part in sp.split_text(block) for q in (_hard_split(part, budget) if ntok(part) > budget else [part])]


def split_section(text: str, budget: int) -> list[str]:
    if ntok(text) <= budget:
        return [text]
    chunks, cur = [], ""
    for kind, block in _blocks(text):
        for piece in [block] if ntok(block) <= budget else _split_block(kind, block, budget):
            joined = f"{cur}\n\n{piece}" if cur else piece
            if cur and ntok(joined) > budget:
                chunks.append(cur)
                cur = piece
            else:
                cur = joined
    if cur:
        chunks.append(cur)
    return chunks


def _can_merge(a: dict, b: dict) -> bool:
    """A tiny section may merge with a neighbour only inside one parent heading: b is a descendant of a
    (page intro -> first H2, empty H2 -> its first H3) or both are H3 siblings under the same H2.
    Never across an H2/H1 boundary."""
    descendant = a["level"] < b["level"] and b["path"][: len(a["path"])] == a["path"]
    siblings = a["level"] == b["level"] == 3 and a["path"][:-1] == b["path"][:-1]
    return descendant or siblings


def _labelled(s: dict) -> str:
    """Section text with its own heading re-inserted, for when it moves under another section's path."""
    return f"{s['path'][-1]}\n{s['text']}".strip() if s["level"] else s["text"]


def _group(parts: list[dict], final: dict) -> dict:
    text = "\n\n".join([_labelled(p) for p in parts] + [final["text"]]).strip()
    return {"path": final["path"], "level": final["level"], "text": text}


def _sections(doc: Doc) -> list[dict]:
    """Sections from MarkdownHeaderTextSplitter as {path, level, text}; tiny ones merged within their parent."""
    md = MarkdownHeaderTextSplitter([("#", "h1"), ("##", "h2"), ("###", "h3")], strip_headers=True)
    secs = []
    for d in md.split_text(doc.text):
        keys = [k for k in ("h1", "h2", "h3") if k in d.metadata]
        path = [doc.title] + [d.metadata[k] for k in keys]
        if len(path) > 1 and path[1] == doc.title:
            del path[1]
        secs.append({"path": path, "level": max((int(k[1]) for k in keys), default=0), "text": d.page_content.strip()})
    out, pending = [], []  # pending: tiny sections waiting to move under the next section
    for s in secs:
        if pending and not _can_merge(pending[-1], s):  # parent boundary: the tiny run stays where it is
            out.append(_group(pending[:-1], pending[-1]))
            pending = []
        if ntok("\n\n".join([_labelled(p) for p in pending] + [s["text"]])) < MIN_SECTION:
            pending.append(s)
            continue
        out.append(_group(pending, s))
        pending = []
    if pending:
        out.append(_group(pending[:-1], pending[-1]))
    # a tiny leftover (e.g. last section under its parent) folds back into its parent/sibling if it fits
    merged = []
    for s in out:
        if merged and ntok(s["text"]) < MIN_SECTION and _can_merge(merged[-1], s) \
                and ntok(merged[-1]["text"] + "\n\n" + _labelled(s)) <= HEADING_TARGET:
            merged[-1]["text"] += "\n\n" + _labelled(s)
        else:
            merged.append(s)
    return merged


def heading_chunks(doc: Doc) -> list[dict]:
    recs = []
    for sec in _sections(doc):
        path, text = sec["path"], sec["text"]
        if not text:
            continue
        hp = " > ".join(path)
        budget = min(HEADING_TARGET, MAX_TOKENS - MARGIN - ntok(hp))
        for piece in split_section(text, budget):
            recs.append(_record(doc, "heading", len(recs), hp, piece))
    return recs


CHUNKERS = {"fixed": fixed_chunks, "heading": heading_chunks}
