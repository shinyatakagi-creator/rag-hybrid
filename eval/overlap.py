"""Term overlap between a question and a passage: the one shared check for golden-set drafting.

A question that reuses a passage's own words flatters BM25. `overlap_ratio` measures how much of the question's
content vocabulary is on the passage; `distinctive_shared` keeps only the shared terms that are rare across the
corpus (those are what BM25 actually latches onto). Tokenisation is deliberately crude: lowercase, camelCase and
punctuation split, stopwords and 1-2 letter tokens dropped, light suffix stemming.
"""
import re
from collections import Counter

STOPWORDS = frozenset(
    "a an and are as at be but by can could do does for from had has have how i if in into is it its me my no not of on "
    "or our so than that the their them then there these they this to up us was we were what when where which who why "
    "will with would you your off out one every about after all any been both each more most other some such only own "
    "same too very just also".split()
)
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def stem(w: str) -> str:
    if len(w) <= 3:
        return w
    for suffix, repl in (("sses", "ss"), ("ies", "y"), ("ing", ""), ("ed", "")):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[: -len(suffix)] + repl
    return w[:-1] if w.endswith("s") and not w.endswith("ss") else w


def content_terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", _CAMEL.sub(" ", text).lower())
    return {stem(w) for w in words if len(w) > 2 and w not in STOPWORDS}


def shared_terms(question: str, passage: str) -> set[str]:
    return content_terms(question) & content_terms(passage)


def overlap_ratio(question: str, passage: str) -> float:
    """Share of the question's content terms that also occur in the passage (0.0 for an empty question)."""
    q = content_terms(question)
    return len(q & content_terms(passage)) / len(q) if q else 0.0


def shared_ngrams(question: str, passage: str, n: int = 4, min_content: int = 2) -> list[str]:
    """Runs of `n` consecutive words that appear in both texts (a copied phrase). Runs made mostly of stopwords
    ("it is possible to") are ignored: at least `min_content` of the n words must be content words."""
    words = lambda t: re.findall(r"[a-z0-9]+", t.lower())
    q, p = words(question), words(passage)
    grams = lambda ws: {tuple(ws[i : i + n]) for i in range(len(ws) - n + 1)}
    return sorted(" ".join(g) for g in grams(q) & grams(p) if sum(w not in STOPWORDS and len(w) > 2 for w in g) >= min_content)


def doc_frequency(texts: list[str]) -> Counter:
    """Number of texts containing each stemmed content term."""
    df: Counter = Counter()
    for t in texts:
        df.update(content_terms(t))
    return df


def distinctive_shared(question: str, passage: str, df: Counter, n_docs: int, max_df: float = 0.2) -> set[str]:
    """Shared terms that appear in fewer than `max_df` of the corpus texts: the ones that give a lexical match away."""
    return {t for t in shared_terms(question, passage) if df[t] / n_docs < max_df}
