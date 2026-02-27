"""Tests for the Vault class."""

from pathlib import Path

import pytest

from vault import Vault


def test_init_valid(tmp_vault: Path):
    v = Vault(tmp_vault)
    assert v.root == tmp_vault.resolve()


def test_init_invalid():
    with pytest.raises(ValueError):
        Vault("/nonexistent/path")


def test_resolve_exact_path(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = v.resolve_path("Projects/spec.md")
    assert result == tmp_vault / "Projects" / "spec.md"


def test_resolve_without_extension(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = v.resolve_path("Projects/spec")
    assert result == tmp_vault / "Projects" / "spec.md"


def test_resolve_by_filename(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = v.resolve_path("ideas")
    assert result is not None
    assert result.name == "ideas.md"


def test_resolve_case_insensitive(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = v.resolve_path("README")
    assert result is not None
    assert result.name == "README.md"


def test_resolve_nonexistent(tmp_vault: Path):
    v = Vault(tmp_vault)
    assert v.resolve_path("does-not-exist") is None


def test_security_boundary(tmp_vault: Path):
    v = Vault(tmp_vault)
    assert v.resolve_path("../../etc/passwd") is None


def test_read_config(tmp_vault: Path):
    v = Vault(tmp_vault)
    config = v.read_config("daily-notes.json")
    assert config["folder"] == "Daily Notes"
    assert config["format"] == "YYYY-MM-DD"


def test_read_config_missing(tmp_vault: Path):
    v = Vault(tmp_vault)
    assert v.read_config("nonexistent.json") == {}


def test_daily_notes_config(tmp_vault: Path):
    v = Vault(tmp_vault)
    config = v.daily_notes_config
    assert config["folder"] == "Daily Notes"
    assert config["format"] == "YYYY-MM-DD"
    assert config["template"] == "Templates/Daily Note"


def test_templates_config(tmp_vault: Path):
    v = Vault(tmp_vault)
    config = v.templates_config
    assert config["folder"] == "Templates"


def test_iter_notes(tmp_vault: Path):
    v = Vault(tmp_vault)
    notes = list(v.iter_notes())
    names = [n.name for n in notes]
    assert "README.md" in names
    # Should not include notes in subdirs when not recursive
    assert "spec.md" not in names


def test_iter_notes_recursive(tmp_vault: Path):
    v = Vault(tmp_vault)
    notes = list(v.iter_notes(recursive=True, max_depth=10))
    names = [n.name for n in notes]
    assert "spec.md" in names
    assert "ideas.md" in names
    assert "README.md" in names


def test_iter_notes_excludes_hidden(tmp_vault: Path):
    v = Vault(tmp_vault)
    notes = list(v.iter_notes(recursive=True, max_depth=10))
    # Should not include anything from .obsidian or .trash
    for n in notes:
        rel = n.relative_to(tmp_vault)
        assert ".obsidian" not in rel.parts
        assert ".trash" not in rel.parts


def test_iter_notes_folder(tmp_vault: Path):
    v = Vault(tmp_vault)
    notes = list(v.iter_notes(folder="Projects"))
    names = [n.name for n in notes]
    assert "spec.md" in names
    assert "ideas.md" in names
    assert "README.md" not in names


def test_ensure_path(tmp_vault: Path):
    v = Vault(tmp_vault)
    p = v.ensure_path("NewFolder/new-note")
    assert p == tmp_vault / "NewFolder" / "new-note.md"
    assert p.parent.is_dir()


def test_ensure_path_security(tmp_vault: Path):
    v = Vault(tmp_vault)
    with pytest.raises(ValueError):
        v.ensure_path("../../escape")


def test_note_count(tmp_vault: Path):
    v = Vault(tmp_vault)
    # spec.md, ideas.md, old-stuff.md, README.md, Daily Note.md template
    assert v.note_count() == 5


def test_folder_count(tmp_vault: Path):
    v = Vault(tmp_vault)
    # Projects, Archive, Daily Notes, Templates
    assert v.folder_count() == 4
