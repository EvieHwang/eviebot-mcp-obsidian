"""Note read/write/edit operations."""

import difflib
import mimetypes
import shutil

import frontmatter
from vault import Vault


def read_note(vault: Vault, path: str, include_frontmatter: bool = True) -> str:
    """Read a note's content, optionally with parsed frontmatter."""
    resolved = vault.resolve_path(path)
    if resolved is None:
        return f"Error: Note not found: {path}"

    # Binary file check
    mime, _ = mimetypes.guess_type(str(resolved))
    if mime and not mime.startswith("text/") and resolved.suffix != ".md":
        stat = resolved.stat()
        return (
            f"[Binary file: {resolved.name}, type: {mime}, size: {stat.st_size} bytes]"
        )

    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        stat = resolved.stat()
        return f"[Binary file: {resolved.name}, size: {stat.st_size} bytes]"

    # Size limit
    if len(content) > 1_000_000:
        content = content[:1_000_000] + "\n\n[Truncated — file exceeds 1MB]"

    if not include_frontmatter:
        return content

    meta, body = frontmatter.parse(content)
    if meta:
        vault_rel = resolved.relative_to(vault.root)
        lines = [f"path: {vault_rel}"]
        lines.append("frontmatter:")
        for k, v in meta.items():
            lines.append(f"  {k}: {v}")
        lines.append("---")
        lines.append(body)
        return "\n".join(lines)

    return content


def write_note(vault: Vault, path: str, content: str) -> str:
    """Create or overwrite a note."""
    try:
        full = vault.ensure_path(path)
    except ValueError as e:
        return f"Error: {e}"

    full.write_text(content, encoding="utf-8")
    vault_rel = full.relative_to(vault.root)
    return f"Wrote {vault_rel}"


def edit_note(vault: Vault, path: str, edits: list[dict], dry_run: bool = False) -> str:
    """Apply text replacements to a note. Returns unified diff."""
    resolved = vault.resolve_path(path)
    if resolved is None:
        return f"Error: Note not found: {path}"

    original = resolved.read_text(encoding="utf-8")
    modified = original

    for edit in edits:
        old_text = edit.get("oldText", "")
        new_text = edit.get("newText", "")
        if old_text not in modified:
            return f"Error: Text not found in note: {old_text[:80]!r}"
        # Only replace first occurrence per edit
        modified = modified.replace(old_text, new_text, 1)

    # Generate diff
    vault_rel = str(resolved.relative_to(vault.root))
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=f"a/{vault_rel}",
        tofile=f"b/{vault_rel}",
    )
    diff_text = "".join(diff)

    if not diff_text:
        return "No changes."

    if not dry_run:
        resolved.write_text(modified, encoding="utf-8")

    prefix = "[DRY RUN] " if dry_run else ""
    return f"{prefix}{diff_text}"


def append_to_note(
    vault: Vault,
    path: str,
    content: str,
    heading: str | None = None,
    create_if_missing: bool = False,
) -> str:
    """Append content to a note, optionally under a heading."""
    resolved = vault.resolve_path(path)

    if resolved is None:
        if not create_if_missing:
            return f"Error: Note not found: {path}"
        try:
            resolved = vault.ensure_path(path)
            resolved.write_text("", encoding="utf-8")
        except ValueError as e:
            return f"Error: {e}"

    existing = resolved.read_text(encoding="utf-8")

    if heading is None:
        # Simple append
        if existing and not existing.endswith("\n"):
            existing += "\n"
        new_content = existing + content
        if not new_content.endswith("\n"):
            new_content += "\n"
        resolved.write_text(new_content, encoding="utf-8")
        vault_rel = resolved.relative_to(vault.root)
        return f"Appended to {vault_rel}"

    # Find heading and insert after its section
    lines = existing.splitlines(keepends=True)
    heading_level = len(heading) - len(heading.lstrip("#"))
    if heading_level == 0:
        # User passed heading without #, try matching
        heading_pattern = heading.strip()
    else:
        heading_pattern = heading.strip()

    insert_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (
            stripped == heading_pattern
            or stripped == f"## {heading}"
            or stripped == f"# {heading}"
            or stripped == f"### {heading}"
        ):
            # Found the heading — now find where its section ends
            insert_idx = i + 1
            # Determine heading level
            h_level = 0
            for ch in stripped:
                if ch == "#":
                    h_level += 1
                else:
                    break

            # Walk forward to find end of section
            for j in range(i + 1, len(lines)):
                sj = lines[j].strip()
                if sj.startswith("#"):
                    jlevel = 0
                    for ch in sj:
                        if ch == "#":
                            jlevel += 1
                        else:
                            break
                    if jlevel <= h_level:
                        insert_idx = j
                        break
                insert_idx = j + 1
            break

    if insert_idx is None:
        # Heading not found — append heading and content at end
        if existing and not existing.endswith("\n"):
            existing += "\n"
        # Determine heading format
        if not heading.startswith("#"):
            heading = f"## {heading}"
        new_content = f"{existing}\n{heading}\n\n{content}\n"
        resolved.write_text(new_content, encoding="utf-8")
    else:
        # Insert content at the found position
        append_text = content if content.endswith("\n") else content + "\n"
        # Ensure blank line before content if needed
        if insert_idx > 0 and lines[insert_idx - 1].strip():
            append_text = "\n" + append_text
        lines.insert(insert_idx, append_text)
        resolved.write_text("".join(lines), encoding="utf-8")

    vault_rel = resolved.relative_to(vault.root)
    return f"Appended under '{heading}' in {vault_rel}"


def delete_note(vault: Vault, path: str, confirm: bool = False) -> str:
    """Delete a note (moves to .trash/)."""
    if not confirm:
        return "Error: Set confirm=True to delete."

    resolved = vault.resolve_path(path)
    if resolved is None:
        return f"Error: Note not found: {path}"

    vault_rel = resolved.relative_to(vault.root)
    trash = vault.root / ".trash"

    if trash.is_dir():
        dest = trash / resolved.name
        # Avoid overwriting in trash
        counter = 1
        while dest.exists():
            dest = trash / f"{resolved.stem}_{counter}{resolved.suffix}"
            counter += 1
        shutil.move(str(resolved), str(dest))
        return f"Moved {vault_rel} to .trash/"
    else:
        resolved.unlink()
        return f"Deleted {vault_rel}"


def move_note(vault: Vault, source: str, destination: str) -> str:
    """Move/rename a note and update wikilinks across the vault."""
    resolved_src = vault.resolve_path(source)
    if resolved_src is None:
        return f"Error: Source note not found: {source}"

    try:
        resolved_dst = vault.ensure_path(destination)
    except ValueError as e:
        return f"Error: {e}"

    if resolved_dst.exists():
        return f"Error: Destination already exists: {destination}"

    old_name = resolved_src.stem
    new_name = resolved_dst.stem

    # Move the file
    shutil.move(str(resolved_src), str(resolved_dst))

    # Update wikilinks across the vault
    updated_count = 0
    if old_name != new_name:
        for note in vault.iter_notes(recursive=True, max_depth=100):
            if note == resolved_dst:
                continue
            content = note.read_text(encoding="utf-8")
            # Replace [[old_name]] references (various forms)
            import re

            pattern = re.compile(
                r"(\[\[)" + re.escape(old_name) + r"(\]\]|\||\#)",
                re.IGNORECASE,
            )
            new_content = pattern.sub(r"\g<1>" + new_name + r"\2", content)
            if new_content != content:
                note.write_text(new_content, encoding="utf-8")
                updated_count += 1

    src_rel = resolved_src.relative_to(vault.root)
    dst_rel = resolved_dst.relative_to(vault.root)
    result = f"Moved {src_rel} → {dst_rel}"
    if updated_count:
        result += (
            f" (updated {updated_count} wikilink{'s' if updated_count != 1 else ''})"
        )
    return result
