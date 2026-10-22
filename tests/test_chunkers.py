from ingest.chunkers import (
    HEADING_TARGET, MAX_TOKENS, _sections, embed_text, fixed_chunks, heading_chunks, make_chunk_id, ntok,
)
from ingest.loaders import Doc


def words(n: int, w: str = "alpha") -> str:
    return " ".join([w] * n)


def doc(text: str, title: str = "T") -> Doc:
    return Doc("concepts/t", "https://kubernetes.io/docs/concepts/t/", title, text)


def paths(d: Doc) -> list[str]:
    return [" > ".join(s["path"]) for s in _sections(d)]


# -- tiny-section merge logic ---------------------------------------------------
def test_all_h3_siblings_tiny_collapse_into_one_chunk():
    d = doc(f"## A\n### a1\n{words(20)}\n### a2\n{words(20)}\n### a3\n{words(20)}")
    secs = _sections(d)
    assert len(secs) == 1 and secs[0]["path"] == ["T", "A", "a3"]
    assert "a1" in secs[0]["text"] and "a2" in secs[0]["text"]  # moved headings stay visible


def test_all_h2_tiny_never_merge_across_h2_boundary():
    d = doc(f"## A\n{words(20)}\n## B\n{words(20)}\n## C\n{words(20)}")
    assert paths(d) == ["T > A", "T > B", "T > C"]


def test_tiny_last_section_folds_back_into_parent_when_it_fits():
    d = doc(f"## A\n{words(200)}\n### a1\n{words(20)}")
    secs = _sections(d)
    assert len(secs) == 1 and secs[0]["path"] == ["T", "A"] and "a1" in secs[0]["text"]


def test_tiny_last_section_stays_under_its_own_h2_after_a_boundary():
    d = doc(f"## A\n{words(200)}\n## B\n{words(20)}")
    assert paths(d) == ["T > A", "T > B"]


def test_tiny_middle_section_moves_into_next_sibling():
    d = doc(f"## A\n### a1\n{words(200)}\n### a2\n{words(20)}\n### a3\n{words(200)}")
    got = {" > ".join(s["path"]): s["text"] for s in _sections(d)}
    assert set(got) == {"T > A > a1", "T > A > a3"}
    assert got["T > A > a3"].startswith("a2")


def test_tiny_last_h3_does_not_cross_into_next_h2():
    d = doc(f"## A\n### a1\n{words(200)}\n### a2\n{words(20)}\n## B\n{words(200)}")
    got = _sections(d)
    assert [" > ".join(s["path"]) for s in got] == ["T > A > a1", "T > B"]  # a2 folded back into a1, not into B
    assert "a2" in got[0]["text"] and "a2" not in got[1]["text"]


def test_intro_before_first_h2_may_merge_into_it():
    d = doc(f"{words(20)}\n## A\n{words(200)}")
    secs = _sections(d)
    assert len(secs) == 1 and secs[0]["path"] == ["T", "A"]


def test_heading_less_page_is_one_section_with_title_path():
    d = doc(words(300))
    secs = _sections(d)
    assert len(secs) == 1 and secs[0]["path"] == ["T"] and secs[0]["level"] == 0
    assert [c["heading_path"] for c in heading_chunks(d)] == ["T"] * len(heading_chunks(d))


def test_merge_that_would_exceed_target_is_refused():
    d = doc(f"## A\n{words(HEADING_TARGET - 30)}\n### a1\n{words(60)}")
    assert paths(d) == ["T > A", "T > A > a1"]  # 60 tiny tokens would push A past the target


def test_h1_equal_to_title_is_not_duplicated_in_path():
    d = doc(f"# T\n{words(200)}")
    assert paths(d) == ["T"]


# -- splitting ----------------------------------------------------------------------
def test_oversize_fence_split_keeps_every_chunk_balanced_and_under_limit():
    code = "\n".join(f"key{i}: value{i} # filler filler filler" for i in range(600))
    d = doc(f"## A\n```yaml\n{code}\n```")
    chunks = heading_chunks(d)
    assert len(chunks) > 1
    for c in chunks:
        assert c["content"].count("```") == 2 and c["token_count"] <= MAX_TOKENS
    body_lines = [l for c in chunks for l in c["content"].split("\n") if l.startswith("key")]
    assert body_lines == code.split("\n")  # nothing lost, nothing duplicated


def test_oversize_table_repeats_header_in_every_chunk():
    rows = "\n".join(f"| name{i} | description of field number {i} with some text |" for i in range(400))
    d = doc(f"## A\n| Field | Description |\n| --- | --- |\n{rows}")
    chunks = heading_chunks(d)
    assert len(chunks) > 1
    for c in chunks:
        assert c["content"].startswith("| Field | Description |\n| --- | --- |")
        assert c["token_count"] <= MAX_TOKENS


def test_table_header_without_leading_pipe_stays_with_its_table():
    rows = "\n".join(f"| name{i} | description of field number {i} with some text |" for i in range(400))
    d = doc(f"## A\nField | Description\n|---|---|\n{rows}")
    chunks = heading_chunks(d)
    assert len(chunks) > 1
    assert all(c["content"].startswith("Field | Description\n|---|---|") for c in chunks)


def test_no_heading_chunk_exceeds_limit_with_long_heading_path():
    long_h = "Very " * 40 + "long heading"
    d = doc(f"## {long_h}\n{words(3000)}")
    assert all(c["token_count"] <= MAX_TOKENS for c in heading_chunks(d))


def test_fixed_chunks_respect_size_and_use_title_path():
    chunks = fixed_chunks(doc(words(2000)))
    assert len(chunks) > 3 and all(c["token_count"] <= 460 for c in chunks)
    assert {c["heading_path"] for c in chunks} == {"T"}
    assert [c["position"] for c in chunks] == list(range(len(chunks)))


def test_token_count_includes_heading_prefix():
    c = heading_chunks(doc(f"## Some heading\n{words(150)}"))[0]
    assert c["token_count"] == ntok(embed_text(c)) > ntok(c["content"])


def test_chunk_id_is_stable_and_content_sensitive():
    a = make_chunk_id("d", "heading", 0, "x")
    assert a == make_chunk_id("d", "heading", 0, "x")
    assert a != make_chunk_id("d", "heading", 0, "y") != make_chunk_id("d", "fixed", 0, "y")
