"""FastMCP server for Obsidian vault operations."""

import os
from datetime import datetime

from fastmcp import FastMCP

import daily_notes as dn
import frontmatter
import links
import notes
import search
import templates
from vault import Vault

vault_path = os.environ.get("OBSIDIAN_VAULT_PATH", "~/Documents/Obsidian")
vault = Vault(vault_path)

mcp = FastMCP("obsidian")


# --- Vault Info ---


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def vault_info() -> str:
    """Get vault metadata and configuration summary."""
    config_dn = vault.daily_notes_config
    config_tmpl = vault.templates_config

    lines = [
        f"Vault: {vault.root}",
        f"Notes: {vault.note_count()}",
        f"Folders: {vault.folder_count()}",
        "",
        "Daily notes config:",
        f"  folder: {config_dn['folder'] or '(root)'}",
        f"  format: {config_dn['format']}",
        f"  template: {config_dn['template'] or '(none)'}",
        "",
        f"Templates folder: {config_tmpl['folder']}",
        "",
        "Recent notes:",
    ]

    # Get 10 most recently modified notes
    all_notes = list(vault.iter_notes(recursive=True, max_depth=100))
    all_notes.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for note in all_notes[:10]:
        rel = note.relative_to(vault.root)
        mtime = datetime.fromtimestamp(note.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"  {rel} ({mtime})")

    return "\n".join(lines)


# --- Note Operations ---


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def read_note(path: str, include_frontmatter: bool = True) -> str:
    """Read a note's content, optionally with parsed frontmatter separated out.

    Args:
        path: Vault-relative path or note name (e.g., "Projects/spec" or just "spec")
        include_frontmatter: If True, return frontmatter as structured data separately from body
    """
    return notes.read_note(vault, path, include_frontmatter)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
def write_note(path: str, content: str) -> str:
    """Create a new note or overwrite an existing one.

    Args:
        path: Vault-relative path (e.g., "Projects/new-idea.md")
        content: Full markdown content (including frontmatter if desired)
    """
    return notes.write_note(vault, path, content)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
def edit_note(path: str, edits: list[dict], dry_run: bool = False) -> str:
    """Make targeted edits to an existing note using text replacement.

    Args:
        path: Vault-relative path or note name
        edits: List of {"oldText": "...", "newText": "..."} replacements
        dry_run: If True, show diff without applying changes
    """
    return notes.edit_note(vault, path, edits, dry_run)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
def append_to_note(
    path: str, content: str, heading: str | None = None, create_if_missing: bool = False
) -> str:
    """Append content to a note, optionally under a specific heading.

    Args:
        path: Vault-relative path or note name
        content: Markdown content to append
        heading: If provided, append under this heading (e.g., "## Notes")
        create_if_missing: Create the note if it doesn't exist
    """
    return notes.append_to_note(vault, path, content, heading, create_if_missing)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
    }
)
def delete_note(path: str, confirm: bool = False) -> str:
    """Delete a note (moves to .trash/ within the vault).

    Args:
        path: Vault-relative path or note name
        confirm: Must be True to proceed with deletion
    """
    return notes.delete_note(vault, path, confirm)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
def move_note(source: str, destination: str) -> str:
    """Move or rename a note, updating wikilinks across the vault.

    Args:
        source: Current vault-relative path
        destination: New vault-relative path
    """
    return notes.move_note(vault, source, destination)


# --- Navigation & Search ---


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def list_notes(folder: str = "", recursive: bool = False, max_depth: int = 2) -> str:
    """List notes in the vault, optionally filtered to a folder.

    Args:
        folder: Vault-relative folder path (empty = vault root)
        recursive: Include notes in subfolders
        max_depth: Maximum folder depth when recursive
    """
    entries = list(
        vault.iter_entries(folder=folder, recursive=recursive, max_depth=max_depth)
    )

    if not entries:
        return f"No entries in {folder or 'vault root'}."

    lines = []
    for entry in entries:
        rel = entry.relative_to(vault.root)
        if entry.is_dir():
            lines.append(f"[DIR]  {rel}/")
        elif entry.suffix == ".md":
            size = entry.stat().st_size
            mtime = datetime.fromtimestamp(entry.stat().st_mtime).strftime("%Y-%m-%d")
            lines.append(f"[NOTE] {rel} ({size}B, {mtime})")
        else:
            size = entry.stat().st_size
            lines.append(f"[FILE] {rel} ({size}B)")

    return "\n".join(lines)


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def search_notes(query: str, folder: str = "", max_results: int = 20) -> str:
    """Full-text search across note content (case-insensitive).

    Args:
        query: Text to search for
        folder: Limit search to a specific folder
        max_results: Maximum number of results
    """
    return search.search_notes(vault, query, folder, max_results)


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def search_by_tag(tag: str) -> str:
    """Find all notes containing a specific tag (inline or frontmatter).

    Args:
        tag: Tag to search for (with or without #, supports nested like "project/active")
    """
    return search.search_by_tag(vault, tag)


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def get_backlinks(path: str) -> str:
    """Find all notes that link to a given note.

    Args:
        path: Vault-relative path or note name
    """
    return links.get_backlinks(vault, path)


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def get_outgoing_links(path: str) -> str:
    """List all wikilinks from a given note with resolution status.

    Args:
        path: Vault-relative path or note name
    """
    return links.get_outgoing_links(vault, path)


# --- Daily Notes ---


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
def get_daily_note(
    offset: int = 0, date: str | None = None, create_if_missing: bool = True
) -> str:
    """Get today's daily note (or another day's), creating from template if needed.

    Args:
        offset: Day offset (0=today, -1=yesterday, 1=tomorrow)
        date: Specific date in YYYY-MM-DD format (overrides offset)
        create_if_missing: Create from template if the note doesn't exist
    """
    return dn.get_daily_note(vault, offset, date, create_if_missing)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
def append_to_daily_note(
    content: str,
    heading: str | None = None,
    offset: int = 0,
    create_if_missing: bool = True,
) -> str:
    """Quick-append to today's daily note.

    Args:
        content: Text to append
        heading: Optional heading to append under (e.g., "## Notes")
        offset: Day offset (0=today)
        create_if_missing: Create the daily note if it doesn't exist
    """
    return dn.append_to_daily_note(vault, content, heading, offset, create_if_missing)


# --- Frontmatter ---


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def get_frontmatter(path: str) -> str:
    """Read a note's YAML frontmatter as structured data.

    Args:
        path: Vault-relative path or note name
    """
    resolved = vault.resolve_path(path)
    if resolved is None:
        return f"Error: Note not found: {path}"

    content = resolved.read_text(encoding="utf-8")
    meta, _ = frontmatter.parse(content)

    if not meta:
        return "No frontmatter."

    lines = []
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
def set_frontmatter(
    path: str, properties: dict, remove_keys: list[str] | None = None
) -> str:
    """Set or update frontmatter properties on a note.

    Args:
        path: Vault-relative path or note name
        properties: Key-value pairs to set (merges with existing)
        remove_keys: Keys to remove from frontmatter
    """
    resolved = vault.resolve_path(path)
    if resolved is None:
        return f"Error: Note not found: {path}"

    content = resolved.read_text(encoding="utf-8")
    meta, body = frontmatter.parse(content)

    # Merge properties
    meta.update(properties)

    # Remove keys
    if remove_keys:
        for key in remove_keys:
            meta.pop(key, None)

    new_content = frontmatter.dump(meta, body)
    resolved.write_text(new_content, encoding="utf-8")

    vault_rel = resolved.relative_to(vault.root)
    return f"Updated frontmatter on {vault_rel}"


# --- Templates ---


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
)
def list_templates() -> str:
    """List available templates in the configured template folder."""
    return templates.list_templates(vault)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
def create_from_template(
    template: str, path: str, variables: dict | None = None
) -> str:
    """Create a new note from a template with variable substitution.

    Args:
        template: Template name (filename without .md)
        path: Where to create the new note
        variables: Custom variable substitutions ({{key}} → value)
    """
    return templates.create_from_template(vault, template, path, variables)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=3001)
