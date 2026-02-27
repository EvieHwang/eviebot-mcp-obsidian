"""Tests for template operations."""

from pathlib import Path

from templates import create_from_template, list_templates
from vault import Vault


def test_list_templates(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = list_templates(v)
    assert "Daily Note" in result
    assert "Templates (1)" in result


def test_list_templates_empty(tmp_vault: Path):
    v = Vault(tmp_vault)
    # Remove template files
    (tmp_vault / "Templates" / "Daily Note.md").unlink()
    result = list_templates(v)
    assert "No templates" in result


def test_create_from_template(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = create_from_template(v, "Daily Note", "Projects/from-template")
    assert "Wrote" in result

    content = (tmp_vault / "Projects" / "from-template.md").read_text()
    # {{title}} should be replaced with "from-template"
    assert "from-template" in content
    # {{date}} should be replaced with today's date
    assert "{{date}}" not in content


def test_create_from_template_custom_vars(tmp_vault: Path):
    v = Vault(tmp_vault)
    # Add a template with custom var
    (tmp_vault / "Templates" / "Custom.md").write_text(
        "Author: {{author}}\n# {{title}}\n"
    )

    result = create_from_template(
        v, "Custom", "Projects/custom-note", variables={"author": "Evie"}
    )
    assert "Wrote" in result

    content = (tmp_vault / "Projects" / "custom-note.md").read_text()
    assert "Author: Evie" in content


def test_create_from_template_not_found(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = create_from_template(v, "Nonexistent", "Projects/new")
    assert "Error:" in result
