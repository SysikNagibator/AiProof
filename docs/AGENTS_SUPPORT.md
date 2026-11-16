# Agent and IDE support

This is the honest status of every integration AiProof ships a registry entry for. The
single source of truth is `src/aiproof/adapters/registry.py`; this page is generated from it
and should be regenerated when the registry changes.

**Legend**

* **support** — the best *realistic* integration tier we expect:
  * `native-hooks` — can observe the lifecycle and **block mid-session**.
  * `mcp-only` — read-only self-check tools over MCP; **cannot block**.
  * `wrapper` — post-hoc only, via `aiproof run -- <agent cmd>`.
* **status** — `verified` (vendor docs read, date recorded), `unverified` (docs not yet
  read), `planned` (registered, not started).

**Totals:** 49 agents — 11 `native-hooks`, 29 `mcp-only`, 9 `wrapper`; 2 `verified`,
5 `unverified`, 42 `planned`.

Only **Claude Code** has a verified native-hooks integration (checked 2026-11-16). The
`generic-cli` wrapper entry is verified as a *mechanism* (`aiproof run -- <cmd>` works for
any CLI), not because every CLI is tested.

## Registry

| id | name | vendor | kind | support | status | verified |
| --- | --- | --- | --- | --- | --- | --- |
| `claude-code` | Claude Code | Anthropic | cli | native-hooks | verified | 2026-11-16 |
| `cursor` | Cursor | Anysphere | ide | native-hooks | planned | — |
| `kiro` | Kiro | AWS | ide | native-hooks | planned | — |
| `gemini-cli` | Gemini CLI | Google | cli | native-hooks | planned | — |
| `qwen-code` | Qwen Code | Alibaba | cli | native-hooks | planned | — |
| `codex-cli` | Codex CLI | OpenAI | cli | native-hooks | unverified | — |
| `opencode` | OpenCode | SST | cli | native-hooks | planned | — |
| `windsurf` | Windsurf | Cognition | ide | native-hooks | unverified | — |
| `junie` | Junie | JetBrains | ide | native-hooks | unverified | — |
| `copilot-cli` | GitHub Copilot CLI | GitHub | cli | native-hooks | unverified | — |
| `goose` | Goose | Block | cli | native-hooks | unverified | — |
| `cline` | Cline | Cline | extension | mcp-only | planned | — |
| `roo-code` | Roo Code | Roo | extension | mcp-only | planned | — |
| `kilo-code` | Kilo Code | Kilo | extension | mcp-only | planned | — |
| `continue` | Continue | Continue | extension | mcp-only | planned | — |
| `zed` | Zed | Zed Industries | ide | mcp-only | planned | — |
| `vscode-copilot` | GitHub Copilot (VS Code) | GitHub | ide | mcp-only | planned | — |
| `jetbrains-ai` | JetBrains AI Assistant | JetBrains | ide | mcp-only | planned | — |
| `amazon-q` | Amazon Q Developer | AWS | cli | mcp-only | planned | — |
| `augment` | Augment Code | Augment | extension | mcp-only | planned | — |
| `warp` | Warp | Warp | terminal | mcp-only | planned | — |
| `crush` | Crush | Charm | cli | mcp-only | planned | — |
| `amp` | Amp | Sourcegraph | cli | mcp-only | planned | — |
| `droid` | Droid | Factory | cli | mcp-only | planned | — |
| `openhands` | OpenHands | All Hands AI | cli | mcp-only | planned | — |
| `trae` | Trae | ByteDance | ide | mcp-only | planned | — |
| `void` | Void | Void | ide | mcp-only | planned | — |
| `tabnine` | Tabnine | Tabnine | extension | mcp-only | planned | — |
| `cody` | Sourcegraph Cody | Sourcegraph | extension | mcp-only | planned | — |
| `firebender` | Firebender | Firebender | extension | mcp-only | planned | — |
| `codebuddy` | CodeBuddy | Tencent | ide | mcp-only | planned | — |
| `qoder` | Qoder | Alibaba | ide | mcp-only | planned | — |
| `iflow-cli` | iFlow CLI | iFlow | cli | mcp-only | planned | — |
| `antigravity` | Antigravity | Google | ide | mcp-only | planned | — |
| `rovodev` | Rovo Dev CLI | Atlassian | cli | mcp-only | planned | — |
| `blackbox` | Blackbox AI | Blackbox | extension | mcp-only | planned | — |
| `refact` | Refact.ai | Refact | extension | mcp-only | planned | — |
| `replit` | Replit Agent | Replit | cloud | mcp-only | planned | — |
| `devin` | Devin | Cognition | cloud | mcp-only | planned | — |
| `codex-cloud` | Codex (cloud) | OpenAI | cloud | mcp-only | planned | — |
| `aider` | Aider | Aider | cli | wrapper | planned | — |
| `open-interpreter` | Open Interpreter | Open Interpreter | cli | wrapper | planned | — |
| `shell-gpt` | shell-gpt | shell-gpt | cli | wrapper | planned | — |
| `llm` | llm (simonw) | Datasette | cli | wrapper | planned | — |
| `ollama` | Ollama | Ollama | cli | wrapper | planned | — |
| `lm-studio` | LM Studio | LM Studio | ide | wrapper | planned | — |
| `llama-cpp` | llama.cpp | ggml | cli | wrapper | planned | — |
| `vllm` | vLLM | vLLM | cli | wrapper | planned | — |
| `generic-cli` | Any CLI agent | - | cli | wrapper | verified | 2026-11-16 |

## Instruction files we protect and scan

`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules`,
`.github/copilot-instructions.md`, `.windsurfrules`, `.clinerules`, `.roorules`, `.rules`,
`.goosehints`, `CONVENTIONS.md`, `.aider.conf.yml`, `.kiro/steering`.

## Installing

```sh
aiproof install --list-ides          # print the table above
aiproof install --ide claude-code    # native hooks (verified)
aiproof install --ide cursor --dry-run
aiproof install --all                # every agent, dry-run by default
```

`mcp-only` agents get an `.mcp.json` entry pointing at `aiproof mcp` (read-only self-check).
`wrapper` agents get a printed `aiproof run -- <cmd>` instruction. See `docs/MCP.md`.

## Promoting an integration

1. Read the vendor's *current* hook/extension documentation.
2. Implement `detect`/`install`/`parse_event`/`respond` in `src/aiproof/adapters/`.
3. Set `support` to the real tier and `status = verified` with the ISO date consulted.
4. Add an E2E test that spawns the entrypoint with realistic stdin.
5. Regenerate this page.

Until then the entry stays `planned`/`unverified`. We do not pretend an integration works.
