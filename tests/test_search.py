"""Tests for search operations."""

from pathlib import Path

from search import search_by_tag, search_notes
from vault import Vault


def test_search_notes(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = search_notes(v, "project spec")
    assert "spec.md" in result


def test_search_notes_case_insensitive(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = search_notes(v, "PROJECT SPEC")
    assert "spec.md" in result


def test_search_notes_no_results(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = search_notes(v, "xyznonexistent")
    assert "No results" in result


def test_search_notes_in_folder(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = search_notes(v, "archived", folder="Archive")
    assert "old-stuff.md" in result


def test_search_by_frontmatter_tag(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = search_by_tag(v, "project")
    assert "spec.md" in result


def test_search_by_inline_tag(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = search_by_tag(v, "legacy")
    assert "old-stuff.md" in result


def test_search_by_tag_with_hash(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = search_by_tag(v, "#project")
    assert "spec.md" in result


def test_search_by_tag_no_results(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = search_by_tag(v, "nonexistent")
    assert "No notes found" in result
