from pathlib import Path

import pytest

from ingest.loaders import Cleaner, doc_id_and_url, in_scope, load_corpus, strip_whats_next


def make_corpus(root: Path) -> Path:
    def w(rel: str, text: str):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf8")

    fm = "---\ntitle: {t}\nweight: 1\n---\n"
    w("docs/concepts/_index.md", fm.format(t="Concepts") + "Intro to concepts.")
    w("docs/concepts/pods/_index.md", fm.format(t="Pods") + "A {{< glossary_tooltip text=\"Pod\" term_id=\"pod\" >}} runs containers.")
    w("docs/tasks/probe.md", fm.format(t="Probes") + (
        '<!-- overview -->\n{{< include "task-tutorial-prereqs.md" >}}\n{{< include "extra.md" >}}\n'
        '## {{% heading "prerequisites" %}}\n{{< note >}}\nCareful\n{{< /note >}}\n'
        '{{% code_sample file="pods/probe.yaml" %}}\n'
        '{{< tabs name="t" >}}\n{{% tab name="Linux" %}}\nrun it\n{{% /tab %}}\n{{< /tabs >}}\n'
        '{{< feature-state for_k8s_version="v1.21" state="stable" >}}\n'
        'see [x]({{< ref "/docs/tasks/other" >}}) {{< skew currentVersion >}}\n'
        '{{< comment >}}hidden{{< /comment >}}'))
    w("docs/reference/kubectl/x.md", fm.format(t="X") + "excluded")
    w("docs/reference/glossary/pod.md", "---\ntitle: Pod\nid: pod\nshort_description: >\n  Smallest unit.\n---\nbody")
    w("docs/reference/config-api/c.md", fm.format(t="Config") + "ok")
    w("docs/setup/other.md", fm.format(t="Out of scope") + "not indexed")
    w("examples/pods/probe.yaml", "apiVersion: v1\nkind: Pod\n")
    w("includes/task-tutorial-prereqs.md", "BOILERPLATE PREREQS")
    w("includes/extra.md", "Extra included text.")
    return root


def test_doc_id_and_url_mapping():
    assert doc_id_and_url(Path("concepts/_index.md")) == ("concepts/_index", "https://kubernetes.io/docs/concepts/")
    assert doc_id_and_url(Path("reference/instrumentation/slis.md"))[1] == "https://kubernetes.io/docs/reference/instrumentation/slis/"


def test_scope_filter(tmp_path):
    docs = load_corpus(make_corpus(tmp_path))
    ids = sorted(d.doc_id for d in docs)
    assert ids == ["concepts/_index", "concepts/pods/_index", "reference/config-api/c", "tasks/probe"]
    assert not any(i.startswith("docs/") for i in ids)  # examples/, includes/, excluded dirs, docs/setup never indexed
    assert not in_scope(Path("reference/kubectl/x.md")) and not in_scope(Path("setup/a.md")) and in_scope(Path("tasks/a.md"))


def test_shortcodes_cleaned_and_references_inlined(tmp_path):
    t = {d.doc_id: d for d in load_corpus(make_corpus(tmp_path))}["tasks/probe"].text
    assert "BOILERPLATE" not in t and "Extra included text." in t
    assert "## Before you begin" in t and "## ## " not in t
    assert "```yaml\napiVersion: v1\nkind: Pod\n```" in t
    assert "Note:" in t and "**Linux**" in t and "Feature state: Kubernetes v1.21 [stable]" in t
    assert "(/docs/tasks/other)" in t and "hidden" not in t
    assert "{{" not in t and "}}" not in t and "<!--" not in t


def test_whats_next_section_is_removed_up_to_the_next_same_or_higher_heading():
    text = "## A\nkeep a\n\n## What's next\n* [link](/x)\n### sub\nmore links\n\n## B\nkeep b\n"
    out, removed = strip_whats_next(text)
    assert out == "## A\nkeep a\n\n## B\nkeep b"
    assert len(removed) == 1 and "sub" in removed[0] and "link" in removed[0]


def test_whats_next_at_end_of_page_and_case_and_anchor_variants():
    out, removed = strip_whats_next("## A\nkeep\n## What’s Next {#next}\n* [x](/x)")
    assert out == "## A\nkeep" and len(removed) == 1


def test_whats_next_inside_a_code_fence_is_not_a_heading():
    text = "## A\n```md\n## What's next\n* not a heading\n```\nafter"
    assert strip_whats_next(text) == (text, [])


def test_whats_next_nested_h3_stops_at_the_next_h3_or_higher():
    out, removed = strip_whats_next("## A\n### What's next\nlinks\n### Other\nkeep\n## B\nkeep b")
    assert out == "## A\n### Other\nkeep\n## B\nkeep b" and len(removed) == 1


def test_text_without_whats_next_is_unchanged_and_other_headings_survive():
    text = "## A\nsee what's next in the text\n## What's more\nx"
    assert strip_whats_next(text) == (text, [])


def test_load_corpus_strips_whats_next_for_every_page(tmp_path):
    root = make_corpus(tmp_path)
    p = root / "docs/concepts/pods/_index.md"
    p.write_text(p.read_text() + '\n\n## {{% heading "whatsnext" %}}\n* [elsewhere](/docs/x)\n', encoding="utf8")
    cleaner = Cleaner(root)
    docs = {d.doc_id: d for d in load_corpus(root, cleaner)}
    assert "What's next" not in docs["concepts/pods/_index"].text and "elsewhere" not in docs["concepts/pods/_index"].text
    assert len(cleaner.whats_next_removed) == 1


def test_glossary_tooltip_becomes_plain_text(tmp_path):
    t = {d.doc_id: d for d in load_corpus(make_corpus(tmp_path))}["concepts/pods/_index"].text
    assert t == "A Pod runs containers."


def test_missing_code_sample_is_reported_not_silent(tmp_path):
    root = make_corpus(tmp_path)
    c = Cleaner(root)
    c.clean('{{% code_sample file="nope.yaml" %}}', root)
    assert c.missing


@pytest.mark.skipif(not Path("data/k8s/docs").exists(), reason="corpus checkout not present")
def test_real_corpus_is_scope_b_511_pages():
    docs = load_corpus(Path("data/k8s"), raw=True)
    assert len(docs) == 511
    assert not any(d.doc_id.startswith(("docs/", "examples/", "includes/")) for d in docs)
