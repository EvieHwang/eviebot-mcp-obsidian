"""Shared test fixtures for Obsidian MCP server tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a temporary Obsidian vault with sample content."""
    # .obsidian config
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    daily_notes_config = {
        "folder": "Daily Notes",
        "format": "YYYY-MM-DD",
        "template": "Templates/Daily Note",
    }
    (obsidian_dir / "daily-notes.json").write_text(json.dumps(daily_notes_config))

    templates_config = {"folder": "Templates"}
    (obsidian_dir / "templates.json").write_text(json.dumps(templates_config))

    # Folders
    (tmp_path / "Projects").mkdir()
    (tmp_path / "Archive").mkdir()
    (tmp_path / "Daily Notes").mkdir()
    (tmp_path / "Templates").mkdir()

    # Sample notes
    (tmp_path / "Projects" / "spec.md").write_text(
        "---\ntitle: Project Spec\ntags:\n  - project\n  - active\n---\n# Spec\n\nThis is a project spec.\n\nSee also [[ideas]].\n"
    )
    (tmp_path / "Projects" / "ideas.md").write_text(
        "# Ideas\n\nSome ideas for the project.\n\n- [[spec]] is the main doc\n- Check [[Archive/old-stuff]] too\n"
    )
    (tmp_path / "Archive" / "old-stuff.md").write_text(
        "---\ntags:\n  - archived\n---\n# Old Stuff\n\nThis is archived. #legacy\n"
    )
    (tmp_path / "README.md").write_text("# My Vault\n\nWelcome to my vault.\n")

    # Template
    (tmp_path / "Templates" / "Daily Note.md").write_text(
        "---\ndate: '{{date}}'\n---\n# {{title}}\n\n## Notes\n\n## Tasks\n"
    )

    # .trash
    trash = tmp_path / ".trash"
    trash.mkdir()

    return tmp_path
