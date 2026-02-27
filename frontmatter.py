"""YAML frontmatter parsing and manipulation for Obsidian notes."""

import yaml


def parse(content: str) -> tuple[dict, str]:
    """Split a note into frontmatter dict and body string.

    Returns ({}, content) if no frontmatter block exists.
    """
    if not content.startswith("---"):
        return {}, content

    # Find closing delimiter
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content

    yaml_text = content[4:end]  # skip opening "---\n"
    body = content[end + 4 :]  # skip "\n---"
    if body.startswith("\n"):
        body = body[1:]

    try:
        metadata = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return {}, content

    if metadata is None:
        return {}, body

    if not isinstance(metadata, dict):
        return {}, content

    return metadata, body


def dump(metadata: dict, body: str) -> str:
    """Reconstruct a note from frontmatter dict and body string.

    Returns just the body if metadata is empty.
    """
    if not metadata:
        return body

    yaml_text = yaml.dump(
        metadata, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    # yaml.dump adds a trailing newline; strip it so we control spacing
    yaml_text = yaml_text.rstrip("\n")
    return f"---\n{yaml_text}\n---\n{body}"
