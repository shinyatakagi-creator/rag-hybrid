from pathlib import Path

import pytest

from eval.overlap import content_terms, distinctive_shared, doc_frequency, overlap_ratio, shared_terms, stem
from ingest.loaders import load_corpus


def test_shared_words_give_a_non_zero_overlap():
    q, p = "how do I stop a fork bomb", "A fork bomb is a process that keeps creating processes until the node is full."
    assert shared_terms(q, p) >= {"fork", "bomb"}
    assert overlap_ratio(q, p) > 0.5  # fork, bomb, stop? -> 2 of {stop, fork, bomb} shared
    assert 0 < overlap_ratio(q, p) <= 1


def test_unrelated_texts_give_zero():
    assert shared_terms("certificate rotation schedule", "pods are scheduled onto nodes by the scheduler") == set()
    assert overlap_ratio("certificate rotation", "banana smoothie recipe") == 0.0


def test_empty_or_all_stopword_question_is_zero_not_an_error():
    assert overlap_ratio("", "anything at all") == 0.0
    assert overlap_ratio("the of to and", "the of to and") == 0.0
    assert content_terms("the of to is it") == set()


def test_light_stemming_matches_inflections():
    assert stem("limits") == stem("limiting") == stem("limit") == "limit"
    assert stem("processes") == stem("process") == "process"
    assert shared_terms("limiting processes", "process limits") == {"limit", "process"}


def test_camel_case_and_flags_are_split():
    assert overlap_ratio("PodReference", "a pod reference object") == 1.0
    assert shared_terms("--max-requests-inflight", "sets max requests inflight") == {"max", "request", "inflight"}


def test_distinctive_shared_ignores_common_words():
    corpus = ["the machine will start a new pod"] * 9 + ["a fork bomb exhausts the machine"]
    df = doc_frequency(corpus)
    q, p = "fork bomb on a machine", "a fork bomb exhausts the machine"
    assert shared_terms(q, p) == {"fork", "bomb", "machine"}
    assert distinctive_shared(q, p, df, len(corpus), max_df=0.5) == {"fork", "bomb"}  # 'machine' is in all 10 texts


@pytest.mark.skipif(not Path("data/k8s/docs").exists(), reason="corpus checkout not present")
def test_regression_the_demo_queries_against_the_pid_limiting_page():
    """The first demo query claimed to avoid the page's terms; a mis-escaped regex reported 0 overlap."""
    docs = load_corpus(Path("data/k8s"))
    page = next(d for d in docs if d.doc_id == "concepts/policy/pid-limiting")
    text = page.title + "\n" + page.text
    df, n = doc_frequency([d.title + "\n" + d.text for d in docs]), len(docs)
    bad = "protect a node from a fork bomb inside one workload that hogs every task slot"
    good = "stop one tenant from exhausting the machine's ability to start new subprocesses"
    assert {"fork", "bomb"} <= distinctive_shared(bad, text, df, n)  # must be non-zero: it leaks the page's own terms
    leak = distinctive_shared(good, text, df, n)
    assert leak <= {"machine"}  # 'machine' sits on 12% of pages, below the 20% cutoff; everything else shared is generic
    assert len(leak) < len(distinctive_shared(bad, text, df, n))
    assert 0 < overlap_ratio(good, text) < overlap_ratio(bad, text)
