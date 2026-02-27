# eviebot-mcp-obsidian — Implementation Plan

## Validated Assumptions

Before building, the actual vault at `~/Documents/Obsidian` was inspected:
- **57 notes** across 3 folders (Archive, w_m, Agentic AIPM)
- Daily notes and templates core plugins are **enabled** but have **no config files** yet (`daily-notes.json`, `templates.json`, `types.json` don't exist)
- No `.trash/` folder exists
- iCloud sync is active (vault is in `~/Documents/Obsidian`)

**Implication:** All config reading must handle missing files gracefully — return sensible defaults (empty folder, `YYYY-MM-DD` format, no template). The `.trash/` directory must be created on first `delete_note` call.

## Tech Stack

- Python 3.12 (pyenv global)
- FastMCP >= 2.0 (HTTP transport, tool registration)
- PyYAML >= 6.0 (frontmatter parsing)
- pytest (testing)
- No additional dependencies needed

## Implementation Phases

### Phase 1: Foundation (vault.py, frontmatter.py, server.py skeleton)

**vault.py** — The `Vault` class that everything else depends on:
- `__init__(vault_path)` — validate path exists, store as Path
- `resolve_path(name_or_path) -> Path` — 3-step resolution (exact → filename+.md → case-insensitive)
- `_validate_within_vault(path)` — security boundary check, resolve symlinks
- `read_config(filename) -> dict` — read `.obsidian/{filename}` JSON, return `{}` if missing
- `daily_notes_config` property — reads `daily-notes.json`, defaults: `{"folder": "", "format": "YYYY-MM-DD", "template": ""}`
- `templates_config` property — reads `templates.json`, defaults: `{"folder": "Templates"}`
- `iter_notes(folder="", recursive=False) -> Iterator[Path]` — yield `.md` files, skip `.obsidian/`, `.trash/`

**frontmatter.py** — Parse and write YAML frontmatter:
- `parse(content: str) -> tuple[dict, str]` — split frontmatter from body, return (metadata, body)
- `dump(metadata: dict, body: str) -> str` — reconstruct note with frontmatter + body
- Preserve key order (use `yaml.dump` with `default_flow_style=False, sort_keys=False`)

**server.py skeleton** — FastMCP app with `vault_info` tool only (validates the server runs and gateway can connect):
- Create `FastMCP("obsidian")` app
- Read `OBSIDIAN_VAULT_PATH` env var
- Instantiate `Vault`
- Register `vault_info` tool
- `uvicorn.run` on `127.0.0.1:3001`

**Tests:** `test_vault.py`, `test_frontmatter.py` — use a temporary vault fixture (tmpdir with sample .md files and `.obsidian/` config).

### Phase 2: Note CRUD (notes.py)

Implement the 6 note operation tools:
- `read_note` — use `vault.resolve_path`, read file, optionally parse frontmatter. Handle binary detection (check first bytes), size limit (1MB truncation).
- `write_note` — `Path.write_text`, create parent dirs with `mkdir(parents=True)`, append `.md` if missing.
- `edit_note` — apply `oldText → newText` replacements, generate unified diff, support `dry_run`.
- `append_to_note` — simple append, or find heading and insert after last line under it. Heading detection: scan for `## Heading` lines, find the section boundary (next heading of same or higher level).
- `delete_note` — move to `.trash/` (create if needed), or permanent delete if `.trash/` is intentionally absent (spec says: "unless .trash/ doesn't exist, in which case it permanently deletes").
- `move_note` — rename file, then scan vault for wikilinks referencing old name and update them.

**Tests:** `test_notes.py` — CRUD operations on temp vault.

### Phase 3: Search & Navigation (search.py, links.py)

**search.py:**
- `search_notes` — walk `.md` files, case-insensitive substring match, return path + line number + context.
- `search_by_tag` — parse both inline `#tag` and frontmatter `tags:` field. Handle nested tags (`#project/active`). Tag regex: `(?<!\w)#([\w/-]+)`.

**links.py:**
- Wikilink regex: `!?\[\[([^\]|#^]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]` — captures note name, ignores heading/alias/embed prefix.
- `get_outgoing_links(path)` — parse note, extract wikilinks, resolve each to check existence.
- `get_backlinks(path)` — scan all vault notes for wikilinks matching the target note name.
- `update_wikilinks(old_name, new_name)` — used by `move_note` to update references vault-wide.

**Tests:** `test_search.py`, `test_links.py`.

### Phase 4: Daily Notes & Templates (daily_notes.py, templates.py)

**daily_notes.py:**
- Moment.js → Python date format mapping. Common tokens: `YYYY`→`%Y`, `MM`→`%m`, `DD`→`%d`, `dddd`→`%A`, `MMMM`→`%B`, `ddd`→`%a`, `MMM`→`%b`, `Do`→custom (ordinal day), `YY`→`%y`, `M`→`%-m`, `D`→`%-d`. Implement a `moment_to_strftime(fmt)` converter.
- `get_daily_note` — compute date, format filename, check if exists, optionally create from template.
- `append_to_daily_note` — resolve daily note path, delegate to `append_to_note`.

**templates.py:**
- `list_templates` — list `.md` files in template folder.
- `create_from_template` — read template, substitute `{{date}}`, `{{title}}`, `{{time}}`, custom vars, write to target path.

**Tests:** `test_daily_notes.py`, `test_templates.py`.

### Phase 5: Server Completion & Integration

- Register all 18 tools in `server.py` with proper tool annotations (readOnlyHint, destructiveHint, idempotentHint).
- Add `.envrc` (`source .venv/bin/activate` + `dotenv .env`).
- Add `requirements.txt`.
- Add `.env.example` with `OBSIDIAN_VAULT_PATH=~/Documents/Obsidian`.
- End-to-end smoke test against the real vault (manual).

### Phase 6: Gateway Integration & Deployment (Human Tasks)

These are human/ops tasks, not code:

1. **Configure Obsidian daily notes** — Open Obsidian on iOS/Mac, set daily notes folder and format in Settings → Core Plugins → Daily Notes. This creates `.obsidian/daily-notes.json`.
2. **Configure Obsidian templates** — Set template folder in Settings → Core Plugins → Templates. This creates `.obsidian/templates.json`.
3. **Update gateway** — In `~/projects/eviebot-MCP-gateway/gateway.py`, replace the `filesystem` proxy with `obsidian` proxy pointing to `127.0.0.1:3001`.
4. **Create launchd plist** — `~/Library/LaunchAgents/com.evie.obsidian-mcp.plist` to auto-start the server.
5. **Retire filesystem server** — Stop and unload `com.evie.filesystem-mcp`, remove from gateway.
6. **Test from Claude.ai** — Verify tools appear under `obsidian_*` namespace, test read/write/search through the gateway.

## Module Dependency Order

```
frontmatter.py  ─┐
                  ├──→ vault.py ──→ notes.py ──→ server.py
                  │                 search.py ──→
                  │                 links.py  ──→
                  │                 daily_notes.py →
                  │                 templates.py ──→
                  └──────────────────────────────────┘
```

`vault.py` depends on `frontmatter.py` for note parsing. All tool modules depend on `vault.py`. `server.py` imports and registers all tools.

## Testing Strategy

- **Fixture:** A `tmp_vault` pytest fixture creates a temp directory with sample notes, folders, frontmatter, wikilinks, and a `.obsidian/` config directory.
- **Unit tests per module** — each module's tests focus on its logic using the fixture.
- **No mocking of the filesystem** — tests use real temp files (it's fast enough for 57-note scale).
- **No integration tests against the real vault** — keep tests isolated and repeatable.
