"""Tests for daily notes operations."""

from datetime import date
from pathlib import Path

from daily_notes import (
    append_to_daily_note,
    format_date,
    get_daily_note,
    moment_to_strftime,
)
from vault import Vault


def test_moment_to_strftime_basic():
    assert "%Y-%m-%d" == moment_to_strftime("YYYY-MM-DD")


def test_format_date_basic():
    d = date(2026, 2, 26)
    assert format_date("YYYY-MM-DD", d) == "2026-02-26"


def test_format_date_with_weekday():
    d = date(2026, 2, 26)
    result = format_date("dddd", d)
    assert result == "Thursday"


def test_format_date_ordinal():
    d = date(2026, 2, 1)
    result = format_date("Do", d)
    assert result == "1st"

    d = date(2026, 2, 3)
    result = format_date("Do", d)
    assert result == "3rd"

    d = date(2026, 2, 11)
    result = format_date("Do", d)
    assert result == "11th"


def test_get_daily_note_creates(tmp_vault: Path):
    v = Vault(tmp_vault)
    today = date.today()
    expected_filename = today.strftime("%Y-%m-%d")

    result = get_daily_note(v, create_if_missing=True)
    assert "path:" in result
    assert expected_filename in result

    # File should exist
    daily_note = tmp_vault / "Daily Notes" / f"{expected_filename}.md"
    assert daily_note.exists()


def test_get_daily_note_from_template(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = get_daily_note(v, create_if_missing=True)
    # Template has {{date}} and {{title}} — should be substituted
    assert "Created" in result


def test_get_daily_note_specific_date(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = get_daily_note(v, date_str="2026-01-15", create_if_missing=True)
    assert "2026-01-15" in result
    assert (tmp_vault / "Daily Notes" / "2026-01-15.md").exists()


def test_get_daily_note_no_create(tmp_vault: Path):
    v = Vault(tmp_vault)
    result = get_daily_note(v, date_str="1999-01-01", create_if_missing=False)
    assert "Error:" in result


def test_append_to_daily_note(tmp_vault: Path):
    v = Vault(tmp_vault)
    today = date.today()
    expected_filename = today.strftime("%Y-%m-%d")

    # Create daily note first
    get_daily_note(v, create_if_missing=True)

    result = append_to_daily_note(v, "Quick thought.")
    assert "Appended" in result

    daily_note = tmp_vault / "Daily Notes" / f"{expected_filename}.md"
    content = daily_note.read_text()
    assert "Quick thought." in content
