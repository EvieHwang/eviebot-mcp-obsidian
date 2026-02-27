"""Tests for note CRUD operations."""

from pathlib import Path

from notes import (
    append_to_note,
    delete_note,
    edit_note,
    move_note,
    read_note,
    write_note,
)
from vault import Vault


def test_read_note(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = read_note(v, "Projects/spec")
    assert "Project Spec" in result
    assert "project spec" in result.lower()


def test_read_note_not_found(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = read_note(v, "nonexistent")
    assert result.startswith("Error:")


def test_read_note_no_frontmatter(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = read_note(v, "Projects/spec", include_frontmatter=False)
    assert result.startswith("---\n")


def test_write_note(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = write_note(v, "new-note", "# New Note\n\nHello world.\n")
    assert "Wrote" in result
    assert (tmp_vault / "new-note.md").exists()
    assert "Hello world" in (tmp_vault / "new-note.md").read_text()


def test_write_note_creates_parents(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = write_note(v, "Deep/Nested/note", "content")
    assert "Wrote" in result
    assert (tmp_vault / "Deep" / "Nested" / "note.md").exists()


def test_edit_note(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = edit_note(
        v,
        "README",
        [{"oldText": "Welcome to my vault.", "newText": "Welcome to the vault."}],
    )
    assert "Welcome" in result
    assert "Welcome to the vault." in (tmp_vault / "README.md").read_text()


def test_edit_note_dry_run(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = edit_note(
        v,
        "README",
        [{"oldText": "Welcome to my vault.", "newText": "Changed."}],
        dry_run=True,
    )
    assert "[DRY RUN]" in result
    assert "Welcome to my vault." in (tmp_vault / "README.md").read_text()


def test_edit_note_text_not_found(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = edit_note(v, "README", [{"oldText": "nonexistent text", "newText": "new"}])
    assert "Error:" in result


def test_append_to_note(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = append_to_note(v, "README", "New line appended.")
    assert "Appended" in result
    content = (tmp_vault / "README.md").read_text()
    assert "New line appended." in content


def test_append_under_heading(tmp_vault: Path):
    v = Vault(tmp_vault)
    # spec.md has "# Spec" heading
    result = append_to_note(v, "Projects/spec", "Added under spec.", heading="# Spec")
    assert "Appended" in result
    content = (tmp_vault / "Projects" / "spec.md").read_text()
    assert "Added under spec." in content


def test_append_create_if_missing(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = append_to_note(v, "brand-new", "First content.", create_if_missing=True)
    assert "Appended" in result
    assert (tmp_vault / "brand-new.md").exists()


def test_delete_note_no_confirm(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = delete_note(v, "README")
    assert "confirm" in result.lower()
    assert (tmp_vault / "README.md").exists()


def test_delete_note_to_trash(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = delete_note(v, "README", confirm=True)
    assert ".trash" in result
    assert not (tmp_vault / "README.md").exists()
    assert (tmp_vault / ".trash" / "README.md").exists()


def test_delete_note_permanent(tmp_vault: Path):
    v = Vault(tmp_vault)
    # Remove .trash to trigger permanent delete
    import shutil

    shutil.rmtree(tmp_vault / ".trash")
    result = delete_note(v, "README", confirm=True)
    assert "Deleted" in result
    assert not (tmp_vault / "README.md").exists()


def test_move_note(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = move_note(v, "Projects/ideas", "Archive/ideas")
    assert "Moved" in result
    assert not (tmp_vault / "Projects" / "ideas.md").exists()
    assert (tmp_vault / "Archive" / "ideas.md").exists()


def test_move_note_updates_wikilinks(tmp_vault: Path):
    v = Vault(tmp_vault)
    # spec.md links to [[ideas]], move ideas to renamed
    move_note(v, "Projects/ideas", "Projects/brainstorm")
    spec_content = (tmp_vault / "Projects" / "spec.md").read_text()
    assert "[[brainstorm]]" in spec_content
    assert "[[ideas]]" not in spec_content
