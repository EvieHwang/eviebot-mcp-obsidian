"""Wikilink parsing, resolution, and backlink indexing."""

import re

from vault import Vault

# Matches [[Note]], [[Note|Alias]], [[Note#Heading]], [[Note#^block]], ![[Embed]]
WIKILINK_PATTERN = re.compile(r"!?\[\[([^\]|#^]+)(?:#[^\]|]*)?(?:\|[^\]]+)?\]\]")


def parse_wikilinks(content: str) -> list[str]:
    """Extract all wikilink target names from content."""
    return WIKILINK_PATTERN.findall(content)


def get_outgoing_links(vault: Vault, path: str) -> str:
    """List all wikilinks from a note with resolution status."""
    resolved = vault.resolve_path(path)
    if resolved is None:
        return f"Error: Note not found: {path}"

    content = resolved.read_text(encoding="utf-8")
    targets = parse_wikilinks(content)

    if not targets:
        vault_rel = resolved.relative_to(vault.root)
        return f"No outgoing links in {vault_rel}."

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in targets:
        t_lower = t.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            unique.append(t)

    lines = []
    for target in unique:
        target_path = vault.resolve_path(target)
        if target_path:
            target_rel = target_path.relative_to(vault.root)
            lines.append(f"  [[{target}]] → {target_rel}")
        else:
            lines.append(f"  [[{target}]] → [broken link]")

    vault_rel = resolved.relative_to(vault.root)
    header = f"Outgoing links from {vault_rel}:\n"
    return header + "\n".join(lines)


def get_backlinks(vault: Vault, path: str) -> str:
    """Find all notes that link to a given note."""
    resolved = vault.resolve_path(path)
    if resolved is None:
        return f"Error: Note not found: {path}"

    target_name = resolved.stem
    target_rel = resolved.relative_to(vault.root)
    results = []

    for note in vault.iter_notes(recursive=True, max_depth=100):
        if note == resolved:
            continue

        try:
            content = note.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        targets = parse_wikilinks(content)
        for t in targets:
            # Match by stem (case-insensitive)
            if t.lower() == target_name.lower() or t.lower().endswith(
                "/" + target_name.lower()
            ):
                # Find the line with the link for context
                note_rel = note.relative_to(vault.root)
                for line in content.splitlines():
                    if f"[[{t}" in line:
                        results.append(f"  {note_rel}: {line.strip()}")
                        break
                else:
                    results.append(f"  {note_rel}")
                break

    if not results:
        return f"No backlinks to {target_rel}."

    header = f"Backlinks to {target_rel} ({len(results)}):\n"
    return header + "\n".join(results)


def update_wikilinks(vault: Vault, old_name: str, new_name: str) -> int:
    """Update all wikilinks referencing old_name to new_name. Returns count of updated files."""
    pattern = re.compile(
        r"(\[\[)" + re.escape(old_name) + r"(\]\]|\||\#)",
        re.IGNORECASE,
    )
    updated = 0
    for note in vault.iter_notes(recursive=True, max_depth=100):
        try:
            content = note.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        new_content = pattern.sub(r"\g<1>" + new_name + r"\2", content)
        if new_content != content:
            note.write_text(new_content, encoding="utf-8")
            updated += 1

    return updated
