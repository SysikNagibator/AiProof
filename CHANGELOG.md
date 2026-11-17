# Changelog

All notable changes to AiProof are documented here. This project uses
[Semantic Versioning](https://semver.org/) and
[Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added
- **Phase 2 — learning from corrections.** `aiproof correct` records a human correction
  (redacted, de-duplicated, grouped) in the ledger. `aiproof learn compile` turns matching
  corrections into disabled rules via a declarative DSL; `learn backtest` replays a rule over
  local git history and recorded commands; `learn enable|disable` (human-only) toggles
  enforcement; `learn export` writes an i18n'd rules block into `AGENTS.md` between marker
  comments without touching user text.
- **`learn_rules` integrity check** — enabled compiled rules are enforced by the gate; a
  `block` rule that matches yields a `fail`. `gate.decide` now also considers `unknown`
  findings. Benchmark scenario 31 proves a learned rule blocks a repeated mistake.
- **CLI parity commands** — `checks`, `watch`, `setup`, `install --ide/--all/--dry-run/--list-ides`,
  `off`, `keys`, `receipt` (alias of `show`), and a global `--lang` flag.
- **TUI** — a dedicated live-feed screen (bounded ring buffer, verdict colors), a
  Rules & Corrections screen showing corrections and compiled rules, and automatic narrow
  layout below ~80 columns.
- **i18n** — `detect_language()` now honors the language saved by `aiproof lang <code>` after
  `AIPROOF_LANG`; added `gate.block.rule` and `learn.*` keys to en/ru.
- **Docs** — full documentation set: `WHY`, `ARCHITECTURE`, `THREAT_MODEL`, `HOOKS`, `CLAIMS`,
  `CHECKS`, `LEDGER`, `I18N`, `TUI`, `BENCH`, `LEARN`, `MCP`, `AGENTS_SUPPORT`, `SIGNING`,
  `DECISIONS`, `DEPENDENCIES`, `CONTRIBUTING`, plus `README_RU.md` and `SKILL.md`.
- **Tooling** — `tools/gen_catalog_report.py`, PyInstaller build scripts, an npm wrapper, MCP
  presets per IDE, and CI/release workflows.

### Changed
- Benchmark expanded from 30 to **31 scenarios**; detection 96%, false positives 0%, median
  latency ~55–80 ms (host-dependent). `docs/BENCH_RESULTS.md` regenerated.
- `DEFAULT_CHECKS` now includes `learn_rules`.
- Full UI localization: all eleven catalogs now cover the same **201 keys** (menu, help,
  doctor, TUI, receipt, updates), with no silent English fallbacks.

### Fixed
- **Tamper-guard bypass.** `Write`/`Edit`/`MultiEdit`/`NotebookEdit` with an absolute
  `file_path` (what editors actually send) evaded the repo-relative protected globs, so an
  agent could edit `.claude/settings.json`, `.git/hooks/*` or `.aiproof/rules.toml`. Protected
  patterns now also match suffix-anchored absolute paths.
- **Session file baseline.** The spec'd `file_snapshot` event was never emitted, so
  `file_changed` could not detect "claimed but identical" for files already dirty at session
  start (the start-commit fallback would wrongly pass them). `SessionStart` (and wrapper mode)
  now record a bounded content-hash snapshot, which the check treats as authoritative.
- **Malformed ledger no longer crashes.** A truncated/corrupt line is reported as a broken
  chain (`MalformedLedgerError`) by `doctor`, `ledger verify`, `show` and `sessions` instead of
  raising; appending after a corrupt tail also recovers.
- **MCP config robustness.** A corrupt or non-object `.mcp.json` no longer crashes
  `aiproof install` / `aiproof uninstall`.
- **Claim-extraction scaling.** Overlapping-claim de-duplication is now linear instead of
  O(n²) (≈6.6 s → ≈0.2 s on 10 000 claims of adversarial input).
- MCP `serverInfo.version` now tracks the package version instead of a hard-coded string.

### Security
- Corrections are redacted before storage, so secrets cannot leak into compiled rules or the
  exported `AGENTS.md` block.

## [0.1.0] — first public build

### Added
- Ledger: append-only, hash-chained JSONL per project with 8 MB rotation and cross-segment
  continuation; `aiproof ledger verify`.
- Redactor: pattern + Shannon-entropy detection with stable, non-reversible placeholders;
  allowlist via `.aiproof/allow.toml`.
- Claims: deterministic multilingual extraction (en, ru, uk, de, es, fr, pt-BR, zh-CN, ja, ko,
  tr) with negation and hedging handling.
- Checks: `commit_exists`, `file_changed`, `tests_ran`, `test_tamper`, `secrets_in_diff`,
  `todo_integrity`, `config_integrity`; `unknown` is never promoted to `pass`.
- Gate (`Stop` hook) with specific, localized, actionable messages and a 2-block cap.
- Tamper guard (`PreToolUse`) and pinned gate settings the agent cannot relax.
- Human-only `pause`/`resume`/`pin` flows requiring an interactive TTY.
- Claude Code adapter (verified 2026-11-16), generic MCP adapter, and wrapper mode
  (`aiproof run -- <cmd>`).
- Read-only stdio MCP server (`aiproof mcp`).
- TUI with green/mono/amber themes, ASCII fallback, layout-independent keys, and non-interactive
  CLI parity.
- Benchmark harness with 30 deterministic scenarios.
- i18n with complete en/ru catalogs and nine machine-draft catalogs.

[Unreleased]: https://github.com/SYSIK/aiproof/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SYSIK/aiproof/releases/tag/v0.1.0
