# eviebot-mcp-obsidian — Spec

## Overview

A purpose-built MCP server for Obsidian vault operations on a headless Mac Mini. Replaces the generic `eviebot-mcp-filesystem` with a vault-native API that understands Obsidian's file format, wikilinks, frontmatter, tags, daily notes, and templates.

**Key design principle:** Operate directly on the vault's markdown files. No dependency on the Obsidian app running, no REST API plugin required. The Mac Mini serves as a headless vault host; iCloud handles sync to iOS devices.

## Architecture

- **Runtime:** Python 3.12+ with FastMCP (consistent with existing gateway)
- **Transport:** HTTP on `127.0.0.1:3001` (same port as current filesystem server)
- **Gateway integration:** Proxied by `eviebot-MCP-gateway` under the `obsidian` namespace (replacing `filesystem`)
- **Vault path:** Configured via environment variable `OBSIDIAN_VAULT_PATH` (e.g., `~/Documents/Obsidian`)
- **Config awareness:** Reads `.obsidian/` config files for daily notes settings, template folder location, and property types

## Module Structure

```
eviebot-mcp-obsidian/
├── server.py              # FastMCP entry point, tool registration
├── vault.py               # Vault class: path resolution, config reading
├── notes.py               # Note read/write/edit operations
├── search.py              # Full-text search, tag search, frontmatter queries
├── links.py               # Wikilink parsing, resolution, backlink indexing
├── daily_notes.py         # Daily note operations (reads .obsidian/daily-notes.json)
├── templates.py           # Template listing and instantiation
├── frontmatter.py         # YAML frontmatter parsing and manipulation
├── tests/
│   ├── test_vault.py
│   ├── test_notes.py
│   ├── test_search.py
│   ├── test_links.py
│   ├── test_daily_notes.py
│   ├── test_templates.py
│   └── test_frontmatter.py
├── CLAUDE.md
├── README.md
├── requirements.txt
└── .envrc
```

## Vault Class (`vault.py`)

Central class that all tools use. Responsible for:

- Resolving note paths relative to vault root (all tool arguments use vault-relative paths, never absolute)
- Reading `.obsidian/daily-notes.json` for daily note configuration (folder, date format, template)
- Reading `.obsidian/templates.json` for template folder location
- Reading `.obsidian/types.json` for property type definitions
- Validating that all resolved paths remain within the vault (security boundary)
- Note name resolution: given a name like `"My Note"`, find `My Note.md` anywhere in the vault (Obsidian-style fuzzy matching by filename)

**Security:** All paths must resolve to within `OBSIDIAN_VAULT_PATH`. Symlinks are resolved and re-checked. Paths into `.obsidian/` are read-only (config reads only, no writes to Obsidian's internal config). The `.trash/` folder is excluded from all operations.

**Path resolution order** (mirrors Obsidian's behavior):
1. Exact path match (e.g., `Projects/my-note.md`)
2. Filename match with `.md` appended (e.g., `my-note` → finds `Projects/my-note.md`)
3. Case-insensitive filename match as fallback

## Tools

### Note Operations

#### `read_note`
Read a note's content, optionally with parsed frontmatter separated out.

```
Args:
    path: str           # Vault-relative path or note name (e.g., "Projects/spec" or just "spec")
    include_frontmatter: bool = True   # If True, return frontmatter as structured YAML separately from body
```

Returns the note content. If `include_frontmatter` is True, returns a structured response with frontmatter fields parsed as key-value pairs and the markdown body separately. This allows Claude to understand metadata without parsing YAML inline.

Binary files (images, PDFs) return metadata only (name, size, type) — no content. Text files over 1MB return a truncation notice.

#### `write_note`
Create a new note or overwrite an existing one.

```
Args:
    path: str           # Vault-relative path (e.g., "Projects/new-idea.md")
    content: str        # Full markdown content (including frontmatter if desired)
```

Creates parent directories as needed. If the file exists, overwrites it. The `.md` extension is appended if not provided.

#### `edit_note`
Make targeted edits to an existing note. Two modes: text replacement and section-based operations.

```
Args:
    path: str
    edits: list[dict]   # List of {"oldText": "...", "newText": "..."} replacements
    dry_run: bool = False
```

Returns a git-style unified diff showing changes. Supports dry_run for previewing edits before applying.

#### `append_to_note`
Append content to an existing note, optionally under a specific heading.

```
Args:
    path: str
    content: str        # Markdown content to append
    heading: str = None # If provided, append under this heading (e.g., "## Notes")
    create_if_missing: bool = False  # Create the note if it doesn't exist
```

If `heading` is provided, finds the heading in the note and inserts the content after the last line under that heading (before the next heading of equal or higher level). If the heading doesn't exist, appends the heading and content at the end of the note.

This is a high-value tool for mobile use — quickly add a thought to a specific note section without reading/rewriting the entire file.

#### `delete_note`
Delete a note.

```
Args:
    path: str
    confirm: bool = False  # Required for safety
```

Moves to `.trash/` within the vault (Obsidian convention) rather than permanent deletion, unless `.trash/` doesn't exist, in which case it permanently deletes.

#### `move_note`
Move or rename a note, updating all wikilinks that reference it across the vault.

```
Args:
    source: str         # Current vault-relative path
    destination: str    # New vault-relative path
```

After moving the file, scans the vault for `[[old-name]]` wikilinks and updates them to `[[new-name]]` (or `[[new-path/new-name]]` if the note moved to a different folder where the short name would be ambiguous). This mirrors Obsidian's native rename behavior.

### Navigation & Search

#### `list_notes`
List notes in the vault, optionally filtered to a folder.

```
Args:
    folder: str = ""     # Vault-relative folder path (empty = vault root)
    recursive: bool = False
    max_depth: int = 2
```

Returns note names, sizes, and modification dates. Excludes `.obsidian/`, `.trash/`, and common noise directories. Directories are listed with `[DIR]` prefix, notes with `[NOTE]` prefix. Non-markdown files are listed with `[FILE]` prefix.

#### `search_notes`
Full-text search across note content.

```
Args:
    query: str          # Text to search for (case-insensitive substring match)
    folder: str = ""    # Limit search to a specific folder
    max_results: int = 20
```

Returns matching notes with the relevant line(s) of context around each match, the note path, and the line number. Searches only `.md` files.

#### `search_by_tag`
Find all notes containing a specific tag.

```
Args:
    tag: str            # Tag to search for (with or without #, supports nested like "project/active")
```

Searches both inline tags (`#tag` in body text) and frontmatter tags (`tags:` property). Returns list of matching note paths.

#### `get_backlinks`
Find all notes that link to a given note.

```
Args:
    path: str           # The note to find backlinks for
```

Scans the vault for `[[note-name]]` wikilinks (and aliases) pointing to the specified note. Returns list of linking notes with the line containing the link for context.

#### `get_outgoing_links`
List all wikilinks from a given note.

```
Args:
    path: str
```

Parses the note for `[[wikilinks]]` and returns them with resolution status (whether the target note exists or is a broken link).

### Daily Notes

#### `get_daily_note`
Get today's daily note (or another day's).

```
Args:
    offset: int = 0     # 0 = today, -1 = yesterday, 1 = tomorrow, etc.
    date: str = None     # Specific date in YYYY-MM-DD format (overrides offset)
    create_if_missing: bool = True  # Create from template if it doesn't exist
```

Reads the daily notes configuration from `.obsidian/daily-notes.json` to determine the folder, date format (Moment.js format string), and template. If the note doesn't exist and `create_if_missing` is True, creates it from the configured template (with basic variable substitution: `{{date}}`, `{{title}}`).

Returns the note content and its vault-relative path.

#### `append_to_daily_note`
Quick-append to today's daily note.

```
Args:
    content: str
    heading: str = None  # Optional heading to append under
    offset: int = 0      # Day offset (0 = today)
    create_if_missing: bool = True
```

Convenience wrapper that combines `get_daily_note` path resolution with `append_to_note`. This is the primary mobile use case: from the Claude iPhone app, quickly jot something into today's daily note.

### Frontmatter

#### `get_frontmatter`
Read a note's YAML frontmatter as structured data.

```
Args:
    path: str
```

Returns parsed frontmatter as key-value pairs. If no frontmatter exists, returns an empty dict.

#### `set_frontmatter`
Set or update frontmatter properties on a note.

```
Args:
    path: str
    properties: dict     # Key-value pairs to set (merges with existing)
    remove_keys: list[str] = []  # Keys to remove from frontmatter
```

Merges the provided properties with existing frontmatter. If the note has no frontmatter block, creates one. Preserves the rest of the note content unchanged.

### Templates

#### `list_templates`
List available templates.

```
Args: (none)
```

Reads the template folder location from `.obsidian/templates.json` and lists all `.md` files in that folder.

#### `create_from_template`
Create a new note from a template.

```
Args:
    template: str       # Template name (filename without .md)
    path: str           # Where to create the new note
    variables: dict = {} # Variable substitutions ({{key}} → value)
```

Copies the template content, performs variable substitution for `{{date}}`, `{{title}}`, `{{time}}`, and any custom variables provided, then writes to the specified path.

### Vault Info

#### `vault_info`
Get vault metadata and configuration.

```
Args: (none)
```

Returns:
- Vault path
- Total note count
- Total folder count
- Daily notes config (folder, format, template) if configured
- Template folder location if configured
- Recent notes (last 10 modified)

This gives Claude a quick orientation to the vault structure at the start of a conversation.

## Tool Annotations

| Tool | Read-Only | Destructive | Idempotent |
|------|-----------|-------------|------------|
| `read_note` | ✓ | - | ✓ |
| `write_note` | - | - | ✓ |
| `edit_note` | - | - | ✓ |
| `append_to_note` | - | - | - |
| `delete_note` | - | ✓ | - |
| `move_note` | - | - | - |
| `list_notes` | ✓ | - | ✓ |
| `search_notes` | ✓ | - | ✓ |
| `search_by_tag` | ✓ | - | ✓ |
| `get_backlinks` | ✓ | - | ✓ |
| `get_outgoing_links` | ✓ | - | ✓ |
| `get_daily_note` | - | - | ✓ |
| `append_to_daily_note` | - | - | - |
| `get_frontmatter` | ✓ | - | ✓ |
| `set_frontmatter` | - | - | ✓ |
| `list_templates` | ✓ | - | ✓ |
| `create_from_template` | - | - | ✓ |
| `vault_info` | ✓ | - | ✓ |

## Dependencies

```
fastmcp>=2.0
pyyaml>=6.0
```

Minimal dependency footprint. No heavy NLP or indexing libraries — this is a text-manipulation server. YAML parsing handles frontmatter; everything else is string operations and filesystem access.

## Configuration

Environment variables:
- `OBSIDIAN_VAULT_PATH` (required): Absolute path to the Obsidian vault root (e.g., `/Users/evie/Documents/Obsidian`)

The server reads Obsidian's own config files from `.obsidian/` for daily notes, templates, and property type settings. No separate config file is needed.

## Gateway Integration

The gateway namespace changes from `filesystem` to `obsidian`. Tool names exposed through the gateway become:
- `obsidian_read_note`
- `obsidian_write_note`
- `obsidian_search_notes`
- etc.

The `launchd` service plist (`com.evie.obsidian-mcp`) replaces `com.evie.filesystem-mcp` on the same port.

## What This Replaces

The `eviebot-mcp-filesystem` server is retired. Its generic file operations are superseded by:

| Old (filesystem) | New (obsidian) |
|---|---|
| `list_directory` | `list_notes` |
| `read_file` | `read_note` |
| `write_file` | `write_note` |
| `edit_file` | `edit_note` |
| `create_directory` | Handled automatically by `write_note` (creates parents) |
| `move` | `move_note` (with wikilink updates) |
| `delete` | `delete_note` (moves to .trash) |
| `search` | `search_notes` (full-text, not glob) |
| `file_info` | `vault_info` + `read_note` metadata |

**New capabilities not in the old server:** `append_to_note`, `get_daily_note`, `append_to_daily_note`, `search_by_tag`, `get_backlinks`, `get_outgoing_links`, `get_frontmatter`, `set_frontmatter`, `list_templates`, `create_from_template`, `vault_info`.

## What This Intentionally Excludes

- **Binary file content:** Images, PDFs, and attachments are metadata-only. Use direct upload to Claude for rich media.
- **Obsidian REST API / plugin dependencies:** Everything operates on files directly.
- **Dataview queries:** Plugin-specific, not part of core Obsidian.
- **Canvas files:** `.canvas` JSON files are a separate Obsidian feature; not included in v1.
- **Full-text indexing / vector search:** Overkill for vault sizes typical of personal use. Simple substring search is sufficient.
- **`.obsidian/` config writes:** The server reads Obsidian config but never modifies it. Obsidian owns its own settings.

## Implementation Notes

### Wikilink Resolution
Obsidian wikilinks use the "shortest unique path" convention. `[[My Note]]` resolves to `My Note.md` anywhere in the vault if the filename is unique. If ambiguous (multiple files named `My Note.md` in different folders), Obsidian uses the full path. The server should mirror this behavior.

Wikilink patterns to parse:
- `[[Note Name]]` — basic link
- `[[Note Name|Display Text]]` — aliased link
- `[[Note Name#Heading]]` — heading link
- `[[Note Name#^block-id]]` — block reference
- `![[Note Name]]` — embed

### Frontmatter Parsing
Obsidian frontmatter is standard YAML between `---` delimiters at the top of the file. The server should parse it robustly, handling:
- String, number, boolean, date values
- Lists (especially `tags:` as a list)
- Nested objects (pass through as-is)
- Wikilinks in frontmatter values (treat as strings, don't resolve)

When writing frontmatter, preserve key order where possible to minimize diff noise.

### Daily Notes Config
The `.obsidian/daily-notes.json` file contains:
```json
{
  "folder": "Daily Notes",
  "format": "YYYY-MM-DD",
  "template": "Templates/Daily Note"
}
```

The `format` field uses Moment.js date format tokens. Common patterns:
- `YYYY-MM-DD` → `2026-02-26`
- `YYYY/MM-MMMM/YYYY-MM-DD-dddd` → `2026/02-February/2026-02-26-Thursday`

The server needs a Moment.js-compatible date formatter (Python's `strftime` doesn't match; use a mapping table or a small library).

### Error Handling
All tools return string results (MCP convention). Errors are returned as descriptive strings, not exceptions. Format: `"Error: {description}"`. This keeps the gateway and Claude's tool-use flow clean.

### Performance
For a personal vault (hundreds to low thousands of notes), no caching or indexing is needed. Operations like `get_backlinks` scan the vault on each call. If performance becomes an issue at scale, an in-memory index can be added later, but it's premature optimization for v1.
