import json
from pathlib import Path

import pytest

from eval import docids
from eval.golden_check import check_file, check_line
from eval.term_stats import report, term_stats

ROWS = [
    {"doc_id": "concepts/policy/pid-limiting", "url": "https://kubernetes.io/docs/concepts/policy/pid-limiting/", "title": "Process ID Limits And Reservations", "chunks_fixed": 3, "chunks_heading": 2},
    {"doc_id": "concepts/workloads/pods/_index", "url": "https://kubernetes.io/docs/concepts/workloads/pods/", "title": "Pods", "chunks_fixed": 5, "chunks_heading": 4},
    {"doc_id": "tasks/job/_index", "url": "https://kubernetes.io/docs/tasks/job/", "title": "Running Jobs", "chunks_fixed": 0, "chunks_heading": 0},
]
DOCS = {r["doc_id"]: r for r in ROWS}


# -- doc ids ----------------------------------------------------------------------------------------
def test_url_to_doc_id_candidates_and_lookup():
    assert docids.candidates_from_url("https://kubernetes.io/docs/concepts/policy/pid-limiting/") == ["concepts/policy/pid-limiting", "concepts/policy/pid-limiting/_index"]
    assert docids.candidates_from_url("https://kubernetes.io/docs/concepts/policy/pid-limiting/#anchor?x=1")[0] == "concepts/policy/pid-limiting"
    assert docids.candidates_from_url("https://example.com/docs/x/") == [] and docids.candidates_from_url("https://kubernetes.io/blog/x/") == []
    assert [r["doc_id"] for r in docids.lookup_url("https://kubernetes.io/docs/concepts/workloads/pods/", ROWS)] == ["concepts/workloads/pods/_index"]
    assert [r["doc_id"] for r in docids.lookup_url("/docs/concepts/policy/pid-limiting", ROWS)] == ["concepts/policy/pid-limiting"]
    assert docids.lookup_url("https://kubernetes.io/docs/reference/kubectl/", ROWS) == []  # excluded folder: not in the list


def test_title_search_and_list_round_trip(tmp_path):
    assert [r["doc_id"] for r in docids.find_title("id LIMITS", ROWS)] == ["concepts/policy/pid-limiting"]  # title is "Process ID Limits ..."
    assert docids.find_title("pid limits", ROWS) == []  # matches titles, not doc_ids
    p = tmp_path / "ids.tsv"
    docids.write_list(ROWS, str(p))
    assert docids.read_list(str(p)) == ROWS


def test_build_rows_counts_chunks_per_chunker(tmp_path):
    corpus = tmp_path / "k8s/docs/concepts"
    corpus.mkdir(parents=True)
    (corpus / "a.md").write_text("---\ntitle: A\n---\nbody", encoding="utf8")
    (corpus / "b.md").write_text("---\ntitle: B\n---\n", encoding="utf8")
    cd = tmp_path / "chunks"
    cd.mkdir()
    for n, k in (("fixed", 2), ("heading", 1)):
        (cd / f"{n}.jsonl").write_text("\n".join(json.dumps({"doc_id": "concepts/a"}) for _ in range(k)), encoding="utf8")
    rows = {r["doc_id"]: r for r in docids.build_rows(str(tmp_path / "k8s"), str(cd))}
    assert (rows["concepts/a"]["chunks_fixed"], rows["concepts/a"]["chunks_heading"]) == (2, 1)
    assert (rows["concepts/b"]["chunks_fixed"], rows["concepts/b"]["chunks_heading"]) == (0, 0)


@pytest.mark.skipif(not Path(docids.LIST_PATH).exists(), reason="doc list not generated")
def test_committed_doc_list_has_502_pages_and_25_without_chunks():
    rows = docids.read_list()
    assert len(rows) == 502 and sum(1 for r in rows if not r["chunks_heading"]) == 25


# -- term stats ---------------------------------------------------------------------------------------
CHUNKS = {
    "fixed": [{"doc_id": "d1", "content": "set --max-requests-inflight here", "heading_path": "A"}, {"doc_id": "d1", "content": "and --Max-Requests-Inflight again", "heading_path": "A"},
              {"doc_id": "d2", "content": "other", "heading_path": "The --max-requests-inflight flag"}],
    "heading": [{"doc_id": "d1", "content": "set --max-requests-inflight here", "heading_path": "A"}, {"doc_id": "d3", "content": "nothing", "heading_path": "B"}],
}


def test_term_stats_counts_chunks_and_docs_per_chunker():
    s = term_stats("--max-requests-inflight", CHUNKS)
    assert (s["fixed"]["chunks"], s["fixed"]["docs"], s["fixed"]["docs_in_heading_path"]) == (2, 1, 1)
    assert (s["heading"]["chunks"], s["heading"]["docs"]) == (1, 1)
    assert s["fixed"]["per_doc"] == [("d1", 2)]


def test_term_stats_case_sensitivity_and_missing_term():
    assert term_stats("--max-requests-inflight", CHUNKS, case=True)["fixed"]["chunks"] == 1  # the capitalised copy no longer matches
    s = term_stats("nonexistent-thing", CHUNKS)
    assert s["fixed"]["chunks"] == 0 and "cannot be answered" in report("nonexistent-thing", s)


# -- golden check -----------------------------------------------------------------------------------------
def good(**kw):
    base = {"id": "e01", "type": "exact_term", "question": "What does the flag do?", "expected_doc_ids": ["concepts/policy/pid-limiting"], "reference_answer": "It limits PIDs.", "answerable": True}
    return {**base, **kw}


def test_a_valid_answerable_and_unanswerable_line_pass():
    assert check_line(good(), DOCS) == ([], [])
    assert check_line(good(id="u01", type="unanswerable", expected_doc_ids=[], reference_answer="", answerable=False), DOCS) == ([], [])
    assert check_line(good(expected_doc_ids=["concepts/policy/pid-limiting", "concepts/workloads/pods/_index"]), DOCS) == ([], [])
    assert check_line(good(note="why this is the right page"), DOCS) == ([], [])  # the optional note field is accepted


@pytest.mark.parametrize("bad,fragment", [
    (good(expected_doc_ids=["concepts/nope"]), "not an indexed page"),
    (good(expected_doc_ids=["tasks/job/_index"]), "no chunks"),
    (good(expected_doc_ids=[]), "at least 1 expected doc"),
    (good(note=5), "note must be a string"),
    (good(other="x"), "keys must be"),
    (good(expected_doc_ids=["concepts/policy/pid-limiting"] * 2), "duplicates"),
    (good(type="weird"), "not in"),
    (good(answerable=False), "answerable=true"),
    (good(type="unanswerable", answerable=False, reference_answer=""), "expected_doc_ids=[]"),  # unanswerable but lists a doc
    (good(type="unanswerable", expected_doc_ids=[], answerable=True), "answerable=false"),
    (good(reference_answer=" "), "reference_answer is required"),
    (good(question="short"), "at least 8"),
    (good(id="has space"), "id must be"),
    (good(question="REPLACE: write me"), "REPLACE"),
    ({k: v for k, v in good().items() if k != "type"}, "missing ['type']"),
])
def test_bad_lines_are_reported(bad, fragment):
    errs, _ = check_line(bad, DOCS)
    assert any(fragment in e for e in errs), errs


MANY = {f"p/{i}": {"doc_id": f"p/{i}", "chunks_fixed": 1, "chunks_heading": 1} for i in range(6)}


def test_more_than_three_expected_docs_is_a_warning_not_an_error():
    errs, warns = check_line(good(expected_doc_ids=[f"p/{i}" for i in range(4)]), MANY)
    assert errs == [] and len(warns) == 1 and "4 expected docs" in warns[0] and "note" in warns[0]


@pytest.mark.parametrize("note", ["these four pages each cover one step", "x"])
def test_a_non_empty_note_silences_the_expected_docs_warning(note):
    assert check_line(good(expected_doc_ids=[f"p/{i}" for i in range(5)], note=note), MANY) == ([], [])


@pytest.mark.parametrize("note", ["", "   "])
def test_an_empty_note_does_not_silence_it(note):
    errs, warns = check_line(good(expected_doc_ids=[f"p/{i}" for i in range(4)], note=note), MANY)
    assert errs == [] and warns


def test_zero_expected_docs_for_an_answerable_question_stays_an_error_even_with_a_note():
    errs, _ = check_line(good(expected_doc_ids=[], note="n/a"), MANY)
    assert any("at least 1" in e for e in errs)


def test_file_check_counts_types_flags_duplicates_and_bad_json(tmp_path):
    p = tmp_path / "g.jsonl"
    p.write_text("\n".join([json.dumps(good()), json.dumps(good()), "{not json", json.dumps(good(id="m1", type="mixed"))]), encoding="utf8")
    errors, counts, summary, warnings = check_file(str(p), ROWS)
    assert any("duplicate id" in e for e in errors[2]) and "invalid JSON" in errors[3][0] and 4 not in errors
    assert counts["exact_term"] == 2 and counts["mixed"] == 1 and "exact_term: 2 (plan 8)" in summary and warnings == {}


def test_warnings_do_not_fail_the_check_command(tmp_path, capsys):
    rows = [{"doc_id": f"p/{i}", "url": "u", "title": "t", "chunks_fixed": 1, "chunks_heading": 1} for i in range(5)]
    from eval import docids
    from eval.golden_check import main
    docids.write_list(rows, str(tmp_path / "ids.tsv"))
    p = tmp_path / "g.jsonl"
    p.write_text(json.dumps(good(expected_doc_ids=[f"p/{i}" for i in range(4)])) + "\n", encoding="utf8")
    assert main([str(p), "--doc-list", str(tmp_path / "ids.tsv")]) == 0  # exit 0: only a warning
    out = capsys.readouterr().out
    assert "warning" in out and "1 warning(s)" in out and "ERROR" not in out
