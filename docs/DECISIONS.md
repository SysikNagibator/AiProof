# Decisions

A running log of the choices that shaped AiProof, and why. Newest themes first; each entry
records the decision and the reasoning so future contributors do not relitigate it blind.

## D1 — distribution names `aiproof-sysik` (PyPI) and `aiproof-sysik` (npm); CLI name `aiproof`

The distribution is **`aiproof-sysik`** on both PyPI and npm. The bare PyPI name `aiproof`
was already taken by an unrelated package when this project started, so publishing under
`aiproof` was impossible. The installed command is still **`aiproof`** and the product is
still **AiProof by SYSIK**.

**Status (2026-11-17): published.** `aiproof-sysik` 0.1.0 is live on
[PyPI](https://pypi.org/project/aiproof-sysik/) and
[npm](https://www.npmjs.com/package/aiproof-sysik). Install with `pipx install aiproof-sysik`,
`pip install aiproof-sysik` or `npm install -g aiproof-sysik`. Future releases use
`.github/workflows/publish.yml` (PyPI OIDC trusted publishing, npm `NPM_TOKEN` secret); it is
manual on purpose, because a published version can never be overwritten.

**Consequence:** `pip install aiproof-sysik` gives the `aiproof` command, which collides with
the unrelated `aiproof` package if someone installs both. This is documented rather than worked
around; `pipx install aiproof-sysik` avoids the ambiguity by isolating the environment. The
npm name `aiproof` is still free, but we deliberately publish under the same
`aiproof-sysik` name on both registries.

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

Neither HMAC nor ed25519 signing is implemented yet. The ledger is an unkeyed SHA-256 hash
chain; `paths.key_path()` and the `[sign]` extra are reserved for the future. Ed25519
signing is declared as a placeholder in `pyproject.toml` so the dependency exists when it
lands.

**Consequence:** receipts prove the chain is internally consistent and unmodified since
writing, not authorship. This is stated in `docs/LEDGER.md`, `docs/SIGNING.md` and the
threat model.

## D7 — `aiproof run -- <cmd>` is post-hoc and cannot block

Wrapper mode observes git state and the process output, then runs the claim checks after
the process exits. There is no mid-session intervention for agents without hooks.

**Consequence:** wrapper mode is a verdict, not a gate. It is labelled as such in the CLI
output and docs. The exit code is the agent's own, except that a blocking verdict returns
`1` when the agent exited `0`, so CI can still fail on a false claim.

## D8 — the TUI is read-only and has documented gaps

The TUI renders status, live feed, sessions, receipts, checks, secrets, rules, settings,
doctor, logs, updates and about, but most screens are **read-only**. Toggling checks,
editing settings, secret allowlisting/redaction, rule enable/backtest/export, the doctor
self-test, log filters, `/` filtering, mouse support and update installation are not
implemented. The default layout hides descriptions below ~80 columns.

**Consequence:** every gap is listed in `docs/TUI.md` rather than claimed as a feature. The
CLI is the non-interactive parity layer for the read-only views.

## D9 — Draft translations ship as `reviewed = false`

Nine catalogs (uk, de, es, fr, pt_br, zh_cn, ja, ko, tr) ship as machine drafts and set
`[meta] reviewed = false`; they cover the full English key set (276 keys) rather than
falling back per key. The UI appends a "(machine-translated)" note from `is_reviewed()`.

**Consequence:** CI fails if any catalog misses a key or a placeholder. Adding a language
is a copy, a translate and a `gen_catalog_report.py` run; reviewing it flips
`[meta] reviewed` to `true` and the note disappears.

## D10 — `AIPROOF_*` environment namespace and `~/.aiproof/`

All environment variables use the `AIPROOF_` prefix; all persistent state lives under
`~/.aiproof/` (override with `AIPROOF_HOME`). `paths.py` is the only module that builds
these paths.

**Consequence:** the tool is easy to sandbox, relocate and test. Tests set
`AIPROOF_DATA_DIR` to a temp dir.
