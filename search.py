"""Full-text search and tag search across vault notes."""

import re

import frontmatter
from vault import Vault


def search_notes(
    vault: Vault, query: str, folder: str = "", max_results: int = 20
) -> str:
    """Full-text search across note content (case-insensitive)."""
    if not query:
        return "Error: Query cannot be empty."

    query_lower = query.lower()
    results = []

    for note in vault.iter_notes(folder=folder, recursive=True, max_depth=100):
        try:
            content = note.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        lines = content.splitlines()
        matches = []
        for i, line in enumerate(lines, 1):
            if query_lower in line.lower():
                matches.append((i, line.strip()))

        if matches:
            vault_rel = note.relative_to(vault.root)
            result_lines = [f"**{vault_rel}**"]
            for line_num, line_text in matches[:3]:  # max 3 matches per file
                result_lines.append(f"  L{line_num}: {line_text}")
            results.append("\n".join(result_lines))

        if len(results) >= max_results:
            break

    if not results:
        return f"No results for: {query}"

    header = f"Found {len(results)} note{'s' if len(results) != 1 else ''} matching '{query}':\n\n"
    return header + "\n\n".join(results)


def search_by_tag(vault: Vault, tag: str) -> str:
    """Find notes containing a specific tag (inline or frontmatter)."""
    # Normalize: strip leading #
    tag = tag.lstrip("#")
    if not tag:
        return "Error: Tag cannot be empty."

    # Pattern for inline tags: #tag (not preceded by word char, not inside a link)
    inline_pattern = re.compile(r"(?<!\w)#" + re.escape(tag) + r"(?!\w)", re.IGNORECASE)

    results = []

    for note in vault.iter_notes(recursive=True, max_depth=100):
        try:
            content = note.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        found = False

        # Check frontmatter tags
        meta, body = frontmatter.parse(content)
        fm_tags = meta.get("tags", [])
        if isinstance(fm_tags, str):
            fm_tags = [fm_tags]
        if isinstance(fm_tags, list):
            for t in fm_tags:
                if isinstance(t, str) and t.lower() == tag.lower():
                    found = True
                    break

        # Check inline tags
        if not found and inline_pattern.search(content):
            found = True

        if found:
            vault_rel = note.relative_to(vault.root)
            results.append(str(vault_rel))

    if not results:
        return f"No notes found with tag: #{tag}"

    header = (
        f"Found {len(results)} note{'s' if len(results) != 1 else ''} with #{tag}:\n\n"
    )
    return header + "\n".join(f"- {r}" for r in results)
