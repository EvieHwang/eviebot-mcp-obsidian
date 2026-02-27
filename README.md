# eviebot-mcp-obsidian

MCP server for Obsidian vault operations on the Mac Mini. Runs as a backend behind the [Eviebot MCP Gateway](https://github.com/EvieHwang/eviebot-MCP-gateway).

Replaces [eviebot-mcp-filesystem](https://github.com/EvieHwang/eviebot-mcp-filesystem) with a vault-native API.

## Status

**Pre-build.** See [SPEC.md](SPEC.md) for the full design specification.

## Design

A purpose-built MCP server that understands Obsidian's file format — wikilinks, frontmatter, tags, daily notes, and templates. Operates directly on markdown files with no dependency on the Obsidian app running or the REST API plugin.

18 tools organized around vault semantics, not filesystem primitives.

## Architecture

- Python 3.12+ / FastMCP
- HTTP transport on `127.0.0.1:3001`
- Proxied by the gateway under the `obsidian` namespace
- Reads `.obsidian/` config for daily notes, templates, and property types
- Vault path configured via `OBSIDIAN_VAULT_PATH` environment variable
