# Obsidian MCP Server

MCP server providing vault-native Obsidian operations for the Eviebot gateway.

## What This Is

A FastMCP server (Python) that provides 18 tools for reading, writing, searching, and managing notes in an Obsidian vault. Runs on `127.0.0.1:3001`, proxied by the gateway at `~/projects/eviebot-MCP-gateway/`.

**Read SPEC.md first** — it contains the full design, all tool signatures, module structure, and implementation notes.

## Key Decisions

- All paths are vault-relative (never absolute)
- No dependency on Obsidian running — direct file operations only
- Reads `.obsidian/` config files (daily-notes.json, templates.json) but never writes to them
- Security: all resolved paths must stay within OBSIDIAN_VAULT_PATH
- Error handling: return descriptive strings, never raise exceptions from tools
- Moment.js date format tokens for daily notes (not Python strftime)

## Running

```bash
OBSIDIAN_VAULT_PATH=~/Documents/Obsidian python server.py  # Starts on 127.0.0.1:3001
pytest  # Run tests
```

## Dependencies

- fastmcp>=2.0
- pyyaml>=6.0
