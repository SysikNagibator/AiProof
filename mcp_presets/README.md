# MCP presets

Ready-made MCP server config blocks for IDEs/agents that connect to `aiproof mcp`.
`aiproof install --ide <id>` writes the generic project-level `.mcp.json` block; the
per-host blocks below are for **manual merging**, because their paths and top-level keys
are unverified and some live inside a larger settings file.

## The canonical block

```json
{
  "mcpServers": {
    "aiproof": {
      "command": "aiproof",
      "args": ["mcp"]
    }
  }
}
```

## Per host

| preset | host | top-level key | notes |
| --- | --- | --- | --- |
| `cursor.json` | Cursor | `mcpServers` | `.cursor/mcp.json` |
| `cline.json` | Cline | `mcpServers` | `.cline/mcp.json` (confirm path) |
| `roo-code.json` | Roo Code | `mcpServers` | `.roo/mcp.json` (confirm path) |
| `kilo-code.json` | Kilo Code | `mcpServers` | Cline fork; confirm path |
| `windsurf.json` | Windsurf | `mcpServers` | `~/.codeium/windsurf/mcp_config.json` |
| `continue.json` | Continue | `mcpServers` | inside `.continue/config.json` |
| `vscode-copilot.json` | GitHub Copilot (VS Code) | `servers` | `.vscode/mcp.json` |
| `zed.json` | Zed | `context_servers` | inside `~/.config/zed/settings.json` |

## Honesty note

These presets are **unverified** unless `docs/AGENTS_SUPPORT.md` records a verification date
for that host. Config file paths, the top-level key (`mcpServers` vs `servers` vs
`context_servers`) and whether the entry lives in a dedicated file or inside a larger settings
file change between vendors and versions. Verify against the host's current documentation
before relying on a preset. `aiproof install --ide <id> --dry-run` shows exactly what would be
written.
