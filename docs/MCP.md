# MCP server

`aiproof mcp` is a **read-only** stdio server implementing the Model Context Protocol,
so MCP-capable agents and IDEs can ask AiProof to verify claims or scan for secrets without
AiProof being able to change any state. It is the integration tier for the ~29 `mcp-only`
agents in `docs/AGENTS_SUPPORT.md`.

## Design

* **Read-only.** No tool can change pins, config, rules or pause state. There is no write
  path in the server.
* **Structured results.** Every tool returns `{"ok": bool, "reason": "..."}` plus data, so
  the model can parse it deterministically.
* **No network.** The server speaks the protocol over stdin/stdout only.
* **Self-check, not a gate.** MCP cannot block mid-session. It helps an agent verify before
  it claims. The real gate is the Claude Code `Stop` hook (`docs/HOOKS.md`).

Implementations: `src/aiproof/mcp/server.py`. Protocol version `2024-11-05`.

## Tools

| tool | input | returns |
| --- | --- | --- |
| `aiproof_status` | `{}` | armed state, pinned-config integrity, ledger status |
| `aiproof_verify_claims` | `{"text": "..."}` | per-claim verdicts, no side effects |
| `aiproof_scan_secrets` | `{}` | findings as type + location + fingerprint |
| `aiproof_receipt` | `{"cwd": "..."}` | the latest session receipt |
| `aiproof_corrections_list` | `{}` | recorded corrections and compiled rules |

Descriptions are one line each to save tokens.

## Installing

```sh
aiproof install --ide cursor --dry-run
aiproof install --ide cursor
aiproof install --all
aiproof install --list-ides
```

`install` writes a **project-level `.mcp.json`** entry pointing at `aiproof mcp`, with a
`.bak` backup and without clobbering existing entries. That path is widely understood and
safe to create; per-host config paths and keys are **not auto-written** because they differ
between vendors/versions and several live inside a larger user settings file. Ready-made
per-host blocks live in `mcp_presets/` for manual merging. The canonical block is:

```json
{
  "mcpServers": {
    "aiproof": { "command": "aiproof", "args": ["mcp"] }
  }
}
```

Hosts that use a different key (`servers` vs `mcpServers`, or `context_servers`, or a
`mcpServers` table inside a larger settings file) need the corresponding preset. Presets
are **unverified** unless `docs/AGENTS_SUPPORT.md` records a verification date for that
host; treat the exact path/key as needing confirmation.

## Running by hand

```sh
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | aiproof mcp
```

The server answers `initialize`, `tools/list` and `tools/call`. `tests/test_mcp.py` drives
it with realistic frames and asserts the read-only contract (a `tools/call` that tried to
mutate state would fail because no such tool exists).
