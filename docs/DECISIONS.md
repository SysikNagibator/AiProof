# Decisions

A running log of the choices that shaped AiProof, and why. Newest themes first; each entry
records the decision and the reasoning so future contributors do not relitigate it blind.

## D1 — PyPI name `aiproof-sysik`, CLI name `aiproof`

The PyPI distribution is **`aiproof-sysik`**. The bare PyPI name `aiproof` was already taken
when this project started, so publishing under `aiproof` was impossible. The installed
command is still **`aiproof`** and the product is still **AiProof by SYSIK**.

**Consequence:** `pip install aiproof-sysik` gives you the `aiproof` command, which
collides with the unrelated `aiproof` package if someone installs both. This is documented
rather than worked around; `pipx install aiproof-sysik` avoids the ambiguity by isolating
the environment. The npm scope is free: `aiproof-sysik` and `aiproof` are both available.

## D2 — Only Claude Code hooks are `verified`

Per spec §4/§15, we never invent hook APIs. On **2026-11-16** the Claude Code hooks
reference and guide were read and its event names, stdin schema, exit codes, JSON decision
schema and `stop_hook_active` behavior were implemented and recorded as `verified`. Every
other agent is `planned` or `unverified` in `src/aiproof/adapters/registry.py`, with
`mcp-only` or `wrapper` as its realistic integration tier.

**Consequence:** the registry is data, not aspiration. `verified` requires a recorded date.
Registrations we have not read the docs for stay `unverified` and are never presented as
working.

## D3 — The gate reads only the pinned copy

Gate-critical keys (`strictness`, `test_command`, `enabled_checks`, `protected_paths`,
`protect_ci`) live in `~/.aiproof/projects/<hash>/pinned.toml`. The in-repo `aiproof.toml`
is advisory and merged only for non-critical keys. `config_integrity` re-verifies the pinned
digest at every Start and Stop.

**Consequence:** an agent editing an in-repo config cannot relax the gate. Changing pinned
settings requires the human-only `aiproof pin`/`aiproof checks` flow from an interactive
TTY.

## D4 — Phase 2 learning is fully implemented, not stubbed

Corrections → compile → DSL rules → backtest → export → **enforced by the `learn_rules`
integrity check**. `gate.decide` now also considers `unknown` findings, and scenario 31
proves an enabled rule blocks a repeated mistake.

**Consequence:** the differentiator actually differentiates. Corrections that do not match a
compile template stay advisory and are labelled "not enforced" everywhere they appear.

## D5 — Backtest false positives are a lower bound

We have no labelled history, so `false_positives` in the backtester counts only explicit
`aiproof:ignore` waivers. The result carries a note saying so.

**Consequence:** the number is honest about its limits rather than presenting a fabricated
precision. See `docs/LEARN.md`.

## D6 — Receipts have no cryptographic signature yet

HMAC via an optional local key is available; ed25519 signing is a **reserved** `[sign]`
extra and is not implemented. The `sign` extra is declared in `pyproject.toml` so the
dependency exists when it lands.

**Consequence:** receipts prove the chain is internally consistent and unmodified since
writing, not authorship. This is stated in `docs/LEDGER.md`, `docs/SIGNING.md` and the
threat model.

## D7 — `aiproof run -- <cmd>` is post-hoc and cannot block

Wrapper mode observes git state and the process output, then runs the claim checks after
the process exits. There is no mid-session intervention for agents without hooks.

**Consequence:** wrapper mode is a verdict, not a gate. It is labelled as such in the CLI
output and docs.

## D8 — TUI filter and mouse handling are gaps

`/` filter and mouse support are stubbed; the default layout hides descriptions below ~80
columns and supports a 60-column minimum.

**Consequence:** documented as gaps in `docs/TUI.md` rather than claimed as features.

## D9 — Draft translations ship as `reviewed = false`

Nine catalogs (uk, de, es, fr, pt_br, zh_cn, ja, ko, tr) ship as machine drafts at 11/62
keys, falling back to English per key, with a "(machine-translated)" note.

**Consequence:** CI fails only for en/ru completeness. Adding a language is a copy, a
translate and a `gen_catalog_report.py` run; reviewing it flips `reviewed` to `true`.

## D10 — `AIPROOF_*` environment namespace and `~/.aiproof/`

All environment variables use the `AIPROOF_` prefix; all persistent state lives under
`~/.aiproof/` (override with `AIPROOF_HOME`). `paths.py` is the only module that builds
these paths.

**Consequence:** the tool is easy to sandbox, relocate and test. Tests set
`AIPROOF_DATA_DIR` to a temp dir.
