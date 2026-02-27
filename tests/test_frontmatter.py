"""Tests for frontmatter parsing and writing."""

from frontmatter import dump, parse


def test_parse_with_frontmatter():
    content = "---\ntitle: Hello\ntags:\n  - one\n  - two\n---\n# Body\n\nSome text.\n"
    meta, body = parse(content)
    assert meta == {"title": "Hello", "tags": ["one", "two"]}
    assert body == "# Body\n\nSome text.\n"


def test_parse_no_frontmatter():
    content = "# Just a heading\n\nNo frontmatter here.\n"
    meta, body = parse(content)
    assert meta == {}
    assert body == content


def test_parse_empty_frontmatter():
    content = "---\n---\n# Body\n"
    meta, body = parse(content)
    assert meta == {}
    assert body == "# Body\n"


def test_parse_invalid_yaml():
    content = "---\n: invalid: yaml: {{{\n---\nBody\n"
    meta, body = parse(content)
    assert meta == {}
    assert body == content


def test_dump_with_metadata():
    meta = {"title": "Test", "tags": ["a", "b"]}
    body = "# Content\n"
    result = dump(meta, body)
    assert result.startswith("---\n")
    assert "title: Test" in result
    assert result.endswith("---\n# Content\n")


def test_dump_empty_metadata():
    body = "# Content\n"
    result = dump({}, body)
    assert result == body


def test_roundtrip():
    original = "---\ntitle: Hello\nstatus: draft\n---\n# Body\n\nContent here.\n"
    meta, body = parse(original)
    rebuilt = dump(meta, body)
    meta2, body2 = parse(rebuilt)
    assert meta == meta2
    assert body == body2
