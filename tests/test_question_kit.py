import json
import re
from collections import Counter
from pathlib import Path

import pytest

from eval import build_question_kit as kit
from eval.docids import read_list
from eval.term_stats import term_stats


def ch(content, doc="concepts/x", heading="X > Y", tok=200):
    return {"doc_id": doc, "content": content, "heading_path": heading, "token_count": tok, "chunk_id": doc + heading, "title": "X"}


# -- candidate extraction -----------------------------------------------------------------------------------------
def test_error_prefix_keeps_the_longest_literal_fragment_and_drops_placeholders():
    assert kit.error_prefix('error: deployment "nginx" exceeded its progress deadline') == "exceeded its progress deadline"
    assert kit.error_prefix("Warning  BackOff              2s (x2 over 3s)  kubelet            Back-off restarting failed container") == "Back-off restarting failed container"
    assert kit.error_prefix('Error from server (NotFound): services "hostnames" not found') == "Error from server (NotFound): services"
    assert kit.error_prefix("error: the server doesn't have a resource type \"deviceclasses\"") == "error: the server doesn't have a resource type"
    assert kit.error_prefix("The connection to the server <server-name:port> was refused - did you specify the right host or port?") is None  # placeholder left over
    assert kit.error_prefix("Kill process 4481 (stress) score 1994 or sacrifice child here") is None  # per-run numbers
    assert kit.error_prefix("error: x") is None  # too short to search for


def test_candidate_extraction_by_kind():
    text = "\n".join([
        "Use `--bind-address` and --max-pods here, the `maxSurge` field, and `controller.kubernetes.io/pod-deletion-cost`.",
        "The annotation foo.bar.io/thing-name is set by the controller.",
        "A label example.com/x and widgets.custom.example.com/widget-name are placeholders, as is apps/v1 and github.com/foo/bar.",
        "Module k8s.io/cloud-provider and gateway.networking.k8s.io/v1.GatewayClass are not keys.",
        "```",
        "Warning  FailedScheduling  23s   default-scheduler  0/42 nodes available",
        "error: you must provide one or more resources by argument",
        "```",
        "An error: outside a code block is prose and not an error string at all, however long it is.",
        "The pod has reason: Evicted and `kubectl get events` shows Normal Scheduled.",
    ])
    c = kit.extract_candidates([ch(text)])
    assert {"--bind-address", "--max-pods"} <= c["flag"] and "maxSurge" in c["field"]
    assert c["annotation"] == {"controller.kubernetes.io/pod-deletion-cost", "foo.bar.io/thing-name"}  # official domain, or 'annotation' nearby; no placeholders / modules / kinds
    assert {"FailedScheduling", "Evicted", "Scheduled"} <= c["reason"]
    assert any(e.startswith("error: you must provide one or more resources") for e in c["error"]) and len(c["error"]) == 2
    assert not any("outside a code block" in e for e in c["error"])


def test_standalone_does_not_match_inside_a_longer_name():
    assert kit.standalone("sets `kubeReserved` here", "kubeReserved") and not kit.standalone("sets kubeReservedCgroup here", "kubeReserved")
    assert kit.standalone("use --max-pods.", "--max-pods") and not kit.standalone("use --max-pods-extra", "--max-pods")


# -- excerpts and facts ---------------------------------------------------------------------------------------------
def test_excerpt_is_3_to_6_lines_balanced_and_never_starts_inside_code():
    content = "```\nold code\nmore\n```\nIntro line that is long enough to count as prose.\nThe `--flag-name` flag sets the thing to a value for you.\nThird prose line follows here.\n```yaml\nkey: value\n```\nTail."
    ex = kit.excerpt(content, "--flag-name")
    lines = ex.split("\n")
    assert 3 <= len(lines) <= 6 and not lines[0].startswith("```") and "--flag-name" in ex
    assert sum(l.startswith("```") for l in lines) % 2 == 0
    assert kit.excerpt("only `--flag-name` here", "--flag-name") is None  # too short to explain anything
    assert kit.excerpt("```\n--flag-name\n```\nx\ny\nz", "--flag-name") is None  # the term is only inside code


def test_error_excerpt_shows_the_message_in_a_balanced_fence_with_leading_prose():
    content = "Before text that is quite long to introduce the output.\nIt looks like this:\n```\nsome earlier line\nerror: you must provide one or more resources\nnext line\n```\nafter"
    ex = kit.excerpt(content, "error: you must provide one or more resources", "error")
    lines = ex.split("\n")
    assert "error: you must provide one or more resources" in ex and lines[0].startswith("Before") and sum(l == "```" for l in lines) == 2
    assert "some earlier line" not in ex  # window is the message and the next line


def test_fact_must_mention_the_term_in_prose_and_say_something_about_it():
    content = ("The `--node-labels` flag sets labels at registration, and a changed value is ignored if the node already exists.\n\n"
               "```\n--node-labels=a=b  # when you run this, nothing happens in code\n```\n\nUnrelated sentence that mentions the default setting.")
    assert kit.extract_fact(content, "--node-labels") == "The `--node-labels` flag sets labels at registration, and a changed value is ignored if the node already exists."
    assert kit.extract_fact("Run `kompose convert --replication-controller --replicas 3` when you want the default.", "--replication-controller") is None
    assert kit.extract_fact("The `kubeReservedCgroup` is not created when it does not exist, by default.", "kubeReserved") is None  # different token
    assert kit.extract_fact("```\nthe flag --x is set when run\n```", "--x") is None
    assert kit.extract_fact("The `--abc-def` flag exists here, simply put as a name.", "--abc-def") is None  # no behaviour / default / condition cue
    assert kit.extract_fact("Set `--a-b` and finish. See the list below.\n\n1. a\n\nThe `--a-b` flag is optional and defaults to off.", "--a-b").endswith("defaults to off.")
    assert kit.extract_fact("Use `--a-b` when needed here.", "--a-b") is None  # cue present but only 5 words
    assert kit.extract_fact("The `--a-b` flag is plain words with no commas and defaults to off.", "--a-b")  # plain letters-only sentences are allowed


# -- rare words --------------------------------------------------------------------------------------------------------
def test_rarest_words_use_whole_tokens_and_skip_stopwords_and_junk():
    pages = ["GenericWorkload and scheduling policy"] + ["scheduling policy and nodes"] * 9
    tokdf = kit.token_frequency(pages)
    assert tokdf["genericworkload"] == 1 and tokdf["generic"] == 0  # camelCase is not split
    got = kit.rarest_words("The GenericWorkload sets scheduling policy; sxzqk is junk", tokdf, k=3)
    assert [w for w, _ in got][0] == "GenericWorkload" and "The" not in [w for w, _ in got] and "sxzqk" not in [w for w, _ in got]
    assert len(kit.rarest_words(" ".join(f"word{i}ing alphabet" for i in range(10)), tokdf, k=5)) <= 5


def test_passage_filters_reject_blobs_link_lists_and_metadata_lines():
    assert kit.passage_lines("Feature state: v1.20 [stable]\nFirst real line.\n```\ncode\n```\nSecond line.") == ["First real line.", "Second line."]
    assert kit._BLOB.search("the key is sxeizblfbaZXCVBNMqwertyuiopasdfghjkl0123 in the middle")
    assert not kit._BLOB.search("see https://example.com/a/very/long/path/that/goes/on/and/on/forever/and/ever/now")
    assert kit._LINK_ITEM.match("* [Install kubectl](/docs/tasks/tools/)")


# -- the generated kit itself (real data) ----------------------------------------------------------------------------------
needs_data = pytest.mark.skipif(not Path("data/chunks/heading.jsonl").exists() or not Path("eval/golden_drafts.jsonl").exists(), reason="chunks / drafts not present")


@pytest.fixture(scope="module")
def built():
    md, data = kit.build()
    return kit.Index(), md, data


@needs_data
def test_a_and_b_terms_meet_every_stated_constraint(built):
    idx, md, data = built
    A, B = data["A"], data["B"]
    assert len(A) == 12 and len(B) == 10 and not {x["term"] for x in A} & {x["term"] for x in B}
    ok_docs = {r["doc_id"] for r in read_list() if r["chunks_fixed"] and r["chunks_heading"]}
    banned = set(data["banned"])
    for it in A + B:
        s = term_stats(it["term"], idx.by_name, case=True)
        assert all(1 <= s[n]["docs"] <= 5 for n in ("fixed", "heading")), it["term"]  # "1-5 docs per eval.term_stats"
        assert it["docs"] and set(it["docs"]) <= ok_docs and it["best_doc"] in ok_docs and not kit.is_generated(it["best_doc"])
        assert not kit.clashes(it["term"], banned), it["term"]
        n = len(it["excerpt"].split("\n"))
        assert 3 <= n <= (6 if it["kind"] != "error" else 6), (it["term"], n)
        assert it["excerpt"].count("```") % 2 == 0
    counts = Counter(x["kind"] for x in A)
    assert set(counts) == {"flag", "field", "annotation", "reason", "error"} and counts["error"] == 2
    page_use = Counter(d for it in A + B for d in it["docs"])
    assert max(page_use.values()) <= kit.MAX_DOCS_PER_PAGE
    for it in B:
        assert it["fact"] and kit.standalone(it["fact"], it["term"]) and it["kind"] != "error"


@needs_data
def test_none_of_the_terms_used_in_drafts_d023_to_d038_is_offered(built):
    _, md, data = built
    used = {json.loads(l)["exact_term"].strip("`").lower() for l in open("eval/golden_drafts.jsonl") if json.loads(l)["id"] >= "d023"}
    offered = {x["term"].lower() for x in data["A"] + data["B"]}
    assert used and not used & offered and not any(kit.clashes(t, used) for t in offered)


@needs_data
def test_c_passages_are_12_distinct_spread_non_generated_pages_with_5_rare_words(built):
    idx, md, data = built
    C = data["C"]
    docs = [p["chunk"]["doc_id"] for p in C]
    assert len(C) == 12 and len(set(docs)) == 12
    assert Counter(d.split("/")[0] for d in docs) == {"concepts": 5, "tasks": 4, "reference": 3}
    drafts = {json.loads(l)["source_doc_id"] for l in open("eval/golden_drafts.jsonl")}
    ab = {d for it in data["A"] + data["B"] for d in it["docs"]}
    assert not set(docs) & (drafts | ab) and not any(kit.is_generated(d) for d in docs)
    for p in C:
        assert 5 <= len(p["excerpt"].split("\n")) <= 10 and len(p["rare"]) == 5
        assert [n for _, n in p["rare"]] == sorted(n for _, n in p["rare"])  # rarest first
        assert not kit._BLOB.search(p["excerpt"]) and "```" not in p["excerpt"]


@needs_data
def test_d_answer_strings_are_absent_from_the_index_and_present_in_the_excluded_source(built):
    idx, md, data = built
    assert len(data["D"]) == 4 and {d["folder"] for d in data["D"]} == {"command-line-tools-reference", "kubectl", "kubernetes-api"}
    for d in data["D"]:
        s = term_stats(d["answer"], idx.by_name)
        assert all(v["chunks"] == 0 for v in s.values()), d["answer"]
        assert d["answer"] in d["fact"] and not d["fact"].endswith(("star", "(se"))  # a whole sentence, not cut mid-word
        assert (Path("data/k8s/docs") / d["source"]).exists()
        doc = d["source"].removesuffix(".md").removeprefix("reference/")
        assert d["source"].split("/")[1] in {"command-line-tools-reference", "kubectl", "kubernetes-api"}
    assert "sourdough" in md and "Jupiter" in md and md.count("no chunk contains this term") >= 6


@needs_data
def test_the_kit_is_deterministic_and_matches_the_committed_file(built):
    _, md, _ = built
    assert md == kit.build()[0]
    if Path(kit.OUT).exists():
        assert Path(kit.OUT).read_text(encoding="utf8") == md, "eval/question_kit.md is stale: run python -m eval.build_question_kit"
    assert md.count("````") % 2 == 0
