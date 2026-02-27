"""Tests for wikilink parsing and backlinks."""

from pathlib import Path

from links import get_backlinks, get_outgoing_links, parse_wikilinks, update_wikilinks
from vault import Vault


def test_parse_basic_wikilink():
    assert parse_wikilinks("See [[My Note]] here.") == ["My Note"]


def test_parse_aliased_wikilink():
    assert parse_wikilinks("See [[My Note|display text]] here.") == ["My Note"]


def test_parse_heading_wikilink():
    assert parse_wikilinks("See [[My Note#Section]] here.") == ["My Note"]


def test_parse_block_ref():
    assert parse_wikilinks("See [[My Note#^block-id]] here.") == ["My Note"]


def test_parse_embed():
    assert parse_wikilinks("![[Image]] here.") == ["Image"]


def test_parse_multiple():
    content = "Link to [[A]] and [[B|alias]] and [[C#heading]]."
    assert parse_wikilinks(content) == ["A", "B", "C"]


def test_parse_none():
    assert parse_wikilinks("No links here.") == []


def test_get_outgoing_links(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = get_outgoing_links(v, "Projects/spec")
    assert "[[ideas]]" in result
    assert "ideas.md" in result


def test_get_outgoing_links_with_broken(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = get_outgoing_links(v, "Projects/ideas")
    # ideas links to [[spec]] (exists) and [[Archive/old-stuff]] (exists)
    assert "spec" in result


def test_get_outgoing_links_not_found(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = get_outgoing_links(v, "nonexistent")
    assert "Error:" in result


def test_get_backlinks(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = get_backlinks(v, "Projects/ideas")
    # spec.md links to [[ideas]]
    assert "spec.md" in result


def test_get_backlinks_none(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = get_backlinks(v, "README")
    assert "No backlinks" in result


def test_update_wikilinks(tmp_vault: Path):
    v = Vault(tmp_vault)
    count = update_wikilinks(v, "ideas", "brainstorm")
    assert count >= 1
    spec_content = (tmp_vault / "Projects" / "spec.md").read_text()
    assert "[[brainstorm]]" in spec_content
