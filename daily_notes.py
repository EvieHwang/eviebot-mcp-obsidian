"""Daily note operations — reads .obsidian/daily-notes.json for config."""

from datetime import date, timedelta

from vault import Vault
import notes


# Moment.js → strftime mapping (most common tokens)
MOMENT_TO_STRFTIME = {
    "YYYY": "%Y",
    "YY": "%y",
    "MMMM": "%B",
    "MMM": "%b",
    "MM": "%m",
    "M": "%-m",
    "DD": "%d",
    "Do": "{ordinal}",  # special handling
    "D": "%-d",
    "dddd": "%A",
    "ddd": "%a",
    "dd": "%a",
    "d": "%w",
    "HH": "%H",
    "H": "%-H",
    "hh": "%I",
    "h": "%-I",
    "mm": "%M",
    "m": "%-M",
    "ss": "%S",
    "s": "%-S",
    "A": "%p",
    "a": "%p",
}


def _ordinal(n: int) -> str:
    """Return ordinal suffix for a number (1st, 2nd, 3rd, etc.)."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def moment_to_strftime(fmt: str) -> str:
    """Convert a Moment.js format string to Python strftime format.

    Processes longer tokens first to avoid partial replacements.
    """
    # Sort by length descending to match longest tokens first
    tokens = sorted(MOMENT_TO_STRFTIME.keys(), key=len, reverse=True)

    result = fmt
    # Use placeholders to avoid double-replacement
    placeholders = {}
    for i, token in enumerate(tokens):
        placeholder = f"\x00{i}\x00"
        if token in result:
            placeholders[placeholder] = MOMENT_TO_STRFTIME[token]
            result = result.replace(token, placeholder, 1)

    for placeholder, strftime_token in placeholders.items():
        result = result.replace(placeholder, strftime_token)

    return result


def format_date(fmt: str, d: date) -> str:
    """Format a date using a Moment.js format string."""
    strftime_fmt = moment_to_strftime(fmt)

    if "{ordinal}" in strftime_fmt:
        strftime_fmt = strftime_fmt.replace("{ordinal}", _ordinal(d.day))

    return d.strftime(strftime_fmt)


def _resolve_date(offset: int = 0, date_str: str | None = None) -> date:
    """Resolve a date from offset or explicit string."""
    if date_str:
        return date.fromisoformat(date_str)
    return date.today() + timedelta(days=offset)


def get_daily_note(
    vault: Vault,
    offset: int = 0,
    date_str: str | None = None,
    create_if_missing: bool = True,
) -> str:
    """Get (or create) a daily note."""
    config = vault.daily_notes_config
    d = _resolve_date(offset, date_str)

    filename = format_date(config["format"], d)
    folder = config["folder"]

    if folder:
        vault_path = f"{folder}/{filename}.md"
    else:
        vault_path = f"{filename}.md"

    resolved = vault.resolve_path(vault_path)

    if resolved and resolved.is_file():
        content = resolved.read_text(encoding="utf-8")
        vault_rel = resolved.relative_to(vault.root)
        return f"path: {vault_rel}\n---\n{content}"

    if not create_if_missing:
        return f"Error: Daily note not found: {vault_path}"

    # Create from template if configured
    template_path = config.get("template", "")
    content = ""
    if template_path:
        template_resolved = vault.resolve_path(template_path)
        if template_resolved and template_resolved.is_file():
            content = template_resolved.read_text(encoding="utf-8")
            # Variable substitution
            content = content.replace("{{date}}", str(d))
            content = content.replace("{{title}}", filename)
            content = content.replace("{{time}}", "")

    result = notes.write_note(vault, vault_path, content)
    if result.startswith("Error"):
        return result

    return f"path: {vault_path}\n[Created]\n---\n{content}"


def append_to_daily_note(
    vault: Vault,
    content: str,
    heading: str | None = None,
    offset: int = 0,
    create_if_missing: bool = True,
) -> str:
    """Quick-append to today's (or another day's) daily note."""
    config = vault.daily_notes_config
    d = _resolve_date(offset)

    filename = format_date(config["format"], d)
    folder = config["folder"]

    if folder:
        vault_path = f"{folder}/{filename}.md"
    else:
        vault_path = f"{filename}.md"

    # Ensure daily note exists
    resolved = vault.resolve_path(vault_path)
    if resolved is None and create_if_missing:
        get_daily_note(vault, offset=offset, create_if_missing=True)

    return notes.append_to_note(
        vault, vault_path, content, heading=heading, create_if_missing=create_if_missing
    )
