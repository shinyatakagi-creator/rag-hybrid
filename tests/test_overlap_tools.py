import json
from pathlib import Path

import pytest

from eval import docids
from eval.golden_check import format_overlap, main as golden_main, overlap_summary
from eval.overlap import detect_exact_terms, doc_frequency, flags_for, page_texts, question_metrics
from eval.overlap_check import analyze, format_report, main as check_main


def chunk(doc, i, content, title=None, heading=None):
    return {"doc_id": doc, "title": title or doc.title(), "heading_path": heading or f"{doc} > s{i}", "content": content, "token_count": 120, "chunk_id": f"{doc}{i}"}


CHUNKS = [
    chunk("pids", 0, "A fork bomb can exhaust process slots. Reserve PIDs for the kubelet and daemons on each node."),
    chunk("pids", 1, "Set the podPidsLimit field on the kubelet to cap process IDs for a Pod."),
    chunk("flags", 0, "Use --max-requests-inflight to bound outstanding work on the API server."),
    chunk("misc", 0, "Generic text about scheduling and nodes and storage and networking."),
] + [chunk(f"filler{i}", 0, "Generic text about scheduling and nodes.") for i in range(8)]


@pytest.fixture()
def chunk_file(tmp_path):
    p = tmp_path / "heading.jsonl"
    p.write_text("\n".join(json.dumps(c) for c in CHUNKS), encoding="utf8")
    return str(p)


# -- shared functions -----------------------------------------------------------------------------------
def test_detect_exact_terms_finds_flags_camel_snake_hyphen_and_backticks():
    q = "What does `maxSurge` do, and is --max-requests-inflight related to pod_name or kube-proxy plain words?"
    assert detect_exact_terms(q) == ["maxSurge", "--max-requests-inflight", "pod_name", "kube-proxy"]
    assert detect_exact_terms("how do I stop a runaway process") == []


def test_exact_term_is_removed_but_the_same_word_used_in_prose_still_counts():
    texts = {"p": "Encryption at rest protects data. The --encryption-config flag selects providers.", **{f"f{i}": "scheduling and nodes" for i in range(9)}}
    df = doc_frequency(list(texts.values()))
    m = question_metrics("How does encryption work with --encryption-config here?", ["--encryption-config"], texts["p"], df, 10)
    assert "encryption" in m["distinctive_shared"]  # 'encryption' in plain prose is a real lexical match (the old code hid it)
    only_term = question_metrics("What does --encryption-config select?", ["--encryption-config"], texts["p"], df, 10)
    assert only_term["distinctive_shared"] == ["select"]  # only the plain word counts; the term's own words ('encryption', 'config') do not


def test_flags_for_exact_term_questions_are_never_flagged():
    m = {"overlap_ratio": 0.99, "distinctive_shared": ["a", "b", "c"], "copied_phrases": ["x y z w"]}
    assert flags_for(m, "exact_term") == [] and flags_for(m, "unanswerable") == []
    assert len(flags_for(m, "conceptual")) == 3


def test_page_texts_joins_title_and_chunks(chunk_file):
    texts, chunks = page_texts(chunk_file)
    assert texts["pids"].startswith("Pids\nA fork bomb") and "podPidsLimit" in texts["pids"] and len(chunks["pids"]) == 2


# -- overlap_check ------------------------------------------------------------------------------------------
def env(chunk_file):
    texts, chunks = page_texts(chunk_file)
    return texts, chunks, doc_frequency(list(texts.values())), len(texts)


def test_a_question_that_reuses_the_page_words_is_flagged_and_a_paraphrase_is_not(chunk_file):
    texts, chunks, df, n = env(chunk_file)
    bad = analyze("The fork bomb can exhaust process slots on the kubelet node", "pids", texts, chunks, df, n)
    assert bad["flags"] and bad["metrics"]["overlap_ratio"] > 0.5 and any(f.startswith("copied_phrase") for f in bad["flags"])
    good = analyze("What keeps one runaway workload from starving the host?", "pids", texts, chunks, df, n)
    assert good["flags"] == [] and good["metrics"]["overlap_ratio"] < 0.3


def test_report_has_ratio_rare_terms_copied_runs_and_best_chunks(chunk_file):
    texts, chunks, df, n = env(chunk_file)
    out = format_report(analyze("fork bomb can exhaust process slots", "pids", texts, chunks, df, n))
    for needle in ("overlap ratio", "shared RARE terms", "copied 4-word runs", "chunks of this page that overlap most", "FLAGGED", "fork", "flag threshold for conceptual: 0.5"):
        assert needle in out
    assert out.index("pids > s0") < out.index("pids > s1")  # the chunk with the shared words comes first


def test_mixed_type_detects_and_removes_the_exact_term(chunk_file):
    texts, chunks, df, n = env(chunk_file)
    a = analyze("Which field such as podPidsLimit caps IDs for a Pod?", "pids", texts, chunks, df, n, typ="mixed")
    assert a["exact_terms"] == ["podPidsLimit"] and "pidslimit" not in " ".join(a["metrics"]["distinctive_shared"])
    assert "exact term(s) taken out" in format_report(a)
    assert analyze("anything", "pids", texts, chunks, df, n, typ="mixed", exact_terms=[])["exact_terms"] == []  # explicit override wins


def test_exact_term_type_reports_but_does_not_flag(chunk_file):
    texts, chunks, df, n = env(chunk_file)
    a = analyze("--max-requests-inflight bound outstanding work API server", "flags", texts, chunks, df, n, typ="exact_term")
    assert a["flags"] == [] and "not flagged by design" in format_report(a)


def test_unknown_doc_is_an_error_with_a_pointer_and_exit_code_2(chunk_file, capsys):
    texts, chunks, df, n = env(chunk_file)
    with pytest.raises(KeyError, match="eval.docids"):
        analyze("q", "nope", texts, chunks, df, n)
    assert check_main(["--question", "fork bomb", "--doc-id", "pids", "--doc-id", "nope", "--chunks", chunk_file]) == 2
    out = capsys.readouterr().out
    assert "page pids" in out and "ERROR" in out  # the good page is still reported


def test_cli_makes_no_network_or_api_import(chunk_file):
    import subprocess, sys
    code = ("import sys; import eval.overlap_check as m; m.main(['--question','fork bomb','--doc-id','pids','--chunks',%r]);"
            "bad=[x for x in ('anthropic','openai','elasticsearch') if x in sys.modules]; print('IMPORTED:',bad)") % chunk_file
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=Path.cwd())
    assert r.returncode == 0 and "IMPORTED: []" in r.stdout, r.stdout + r.stderr


# -- golden_check overlap summary ----------------------------------------------------------------------------------
def golden_file(tmp_path, lines):
    p = tmp_path / "g.jsonl"
    p.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf8")
    return str(p)


def q(id, typ, question, docs, **kw):
    return {"id": id, "type": typ, "question": question, "expected_doc_ids": docs, "reference_answer": "a" if docs else "", "answerable": bool(docs), **kw}


def test_summary_groups_by_type_uses_worst_case_over_expected_docs_and_skips_unanswerable(chunk_file, tmp_path):
    texts, _ = page_texts(chunk_file)
    df, n = doc_frequency(list(texts.values())), len(texts)
    p = golden_file(tmp_path, [
        q("c1", "conceptual", "The fork bomb can exhaust process slots on the kubelet node", ["pids"]),
        q("c2", "conceptual", "What keeps one runaway workload from starving the host?", ["pids", "misc"]),
        q("m1", "mixed", "Which field such as podPidsLimit caps IDs for a Pod?", ["pids"]),
        q("e1", "exact_term", "--max-requests-inflight bound outstanding work API server", ["flags"]),
        q("u1", "unanswerable", "How do I run a Terraform module in a pod?", []),
        q("x1", "conceptual", "unknown page question here ok", ["not-a-page"]),
    ])
    summary, rows = overlap_summary(p, texts, df, n)
    assert set(summary) == {"exact_term", "conceptual", "mixed"} and summary["conceptual"]["n"] == 2  # unanswerable and unknown-doc lines skipped
    assert summary["conceptual"]["flagged"] == 1 and summary["exact_term"]["flagged"] is None
    c1 = next(r for r in rows if r["id"] == "c1")
    assert c1["flagged"] and c1["copied_phrase"] and c1["worst_doc"] == "pids"
    two_docs = next(r for r in rows if r["id"] == "c2")
    assert two_docs["overlap_ratio"] == max(question_metrics("What keeps one runaway workload from starving the host?", [], texts[d], df, n)["overlap_ratio"] for d in ("pids", "misc"))
    assert next(r for r in rows if r["id"] == "m1")["exact_terms"] == ["podPidsLimit"]
    text = format_overlap(summary)
    assert "conceptual" in text and "n/a (by design)" in text and "rare terms" in text


def test_golden_check_prints_the_summary_and_can_save_it(chunk_file, tmp_path, capsys):
    ids = tmp_path / "ids.tsv"
    docids.write_list([{"doc_id": d, "url": "u", "title": "t", "chunks_fixed": 1, "chunks_heading": 1} for d in ("pids", "flags", "misc")], str(ids))
    p = golden_file(tmp_path, [q("c1", "conceptual", "The fork bomb can exhaust process slots on the kubelet node", ["pids"])])
    out_json = tmp_path / "overlap.json"
    assert golden_main([p, "--doc-list", str(ids), "--chunks", chunk_file, "--json-out", str(out_json)]) == 0
    printed = capsys.readouterr().out
    assert "overlap of each answerable question" in printed and "conceptual" in printed and f"saved {out_json}" in printed
    saved = json.loads(out_json.read_text())
    assert saved["by_type"]["conceptual"]["n"] == 1 and saved["questions"][0]["id"] == "c1"
    assert golden_main([p, "--doc-list", str(ids), "--chunks", chunk_file, "--no-overlap"]) == 0
    assert "overlap of each answerable question" not in capsys.readouterr().out


def test_missing_chunk_file_skips_the_summary_without_failing(tmp_path, capsys):
    ids = tmp_path / "ids.tsv"
    docids.write_list([{"doc_id": "pids", "url": "u", "title": "t", "chunks_fixed": 1, "chunks_heading": 1}], str(ids))
    p = golden_file(tmp_path, [q("c1", "conceptual", "The fork bomb can exhaust process slots on the kubelet node", ["pids"])])
    assert golden_main([p, "--doc-list", str(ids), "--chunks", str(tmp_path / "missing.jsonl")]) == 0
    assert "overlap summary skipped" in capsys.readouterr().out
