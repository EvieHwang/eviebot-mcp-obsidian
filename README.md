# eviebot-mcp-obsidian

An MCP server that gives Claude direct access to an Obsidian vault. Read, write, search, and manage notes — including daily notes, templates, wikilinks, tags, and frontmatter — all through natural conversation.

Runs on a headless Mac Mini behind the [Eviebot MCP Gateway](https://github.com/EvieHwang/eviebot-MCP-gateway). No Obsidian app or plugins required; operates directly on the vault's markdown files.

## Tools

**Notes** — `read_note`, `write_note`, `edit_note`, `append_to_note`, `delete_note`, `move_note`

**Search** — `search_notes` (full-text), `search_by_tag`, `get_backlinks`, `get_outgoing_links`

**Daily Notes** — `get_daily_note`, `append_to_daily_note`

**Frontmatter** — `get_frontmatter`, `set_frontmatter`

**Templates** — `list_templates`, `create_from_template`

**Vault** — `vault_info`, `list_notes`

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
OBSIDIAN_VAULT_PATH=~/Documents/Obsidian python server.py
```

The server starts on `127.0.0.1:3001`. The gateway proxies it under the `obsidian` namespace, so tools appear as `obsidian_read_note`, `obsidian_search_notes`, etc.

## Configuration

The only required config is the `OBSIDIAN_VAULT_PATH` environment variable. Everything else is read from Obsidian's own config files (`.obsidian/daily-notes.json`, `.obsidian/templates.json`), with sensible defaults when those files don't exist.

## Testing

```bash
pytest
```

78 tests covering all modules. Tests use a temporary vault fixture — no real vault access needed.

## Design Details

See [SPEC.md](SPEC.md) for the full specification: tool signatures, path resolution behavior, wikilink parsing, Moment.js date format mapping, and security boundaries.
