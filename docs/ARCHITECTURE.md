# Architecture

AiProof is a local verification layer that sits between an AI coding agent and the
user's sense of "done". This document describes how the pieces fit together.

## Design constraints (non-negotiable)

1. **Local & offline.** No network calls in any verification path. No telemetry.
2. **Deterministic.** Claim extraction and all checks are pure functions of local
   state (git, files, ledger). No model is used to decide anything.
3. **Fail-open.** An internal error must never brick the agent. Errors are logged
   and surfaced, never escalated into an agent-blocking crash.
4. **Human-in-the-loop for disarm.** Pausing, re-pinning and uninstalling require a
   real interactive TTY; an agent cannot call them.
5. **Honesty about integrations.** We never invent hook event names or config paths.
   Unverified integrations are labelled as such (see [`AGENTS_SUPPORT.md`](AGENTS_SUPPORT.md)).

## Component map

```
                       ┌──────────────────────────────────────────────┐
  agent lifecycle ───▶ │ hooks/entry.py  (fast, fail-open dispatcher)  │
  (stdin JSON)         └───────────────┬──────────────────────────────┘
                                       │ normalize via adapter
                                       ▼
                       ┌──────────────────────────────────────────────┐
                       │ adapters/   (registry + per-agent adapters)   │
                       └───────────────┬──────────────────────────────┘
                                       │
             ┌─────────────────────────┼───────────────────────────┐
             ▼                         ▼                           ▼
      guard/tamper_guard        ledger/store.py             redact/
      (PreToolUse deny)     (append, hash-chain, rotate)  (pattern+entropy)
                                       │
                    Stop / "done"      ▼
                       ┌──────────────────────────────────────────────┐
                       │ claims/extractor.py (multilingual, no model)  │
                       └───────────────┬──────────────────────────────┘
                                       ▼
                       ┌──────────────────────────────────────────────┐
                       │ checks/  (commit_exists, file_changed,        │
                       │           tests_ran, test_tamper, secrets,    │
                       │           todo_integrity, config_integrity)   │
                       └───────────────┬──────────────────────────────┘
                                       ▼
                       ┌──────────────────────────────────────────────┐
                       │ gate/gate.py  (strictness → block?)           │
                       │ gate/messages.py (localized reason)           │
                       └───────────────┬──────────────────────────────┘
                                       ▼
                           block the agent's "done"
                       (or record a receipt in observe/warn)
```

## Data flow, step by step

1. The agent fires a lifecycle event. An adapter normalizes the payload into an
   `Event` (`adapters/base.py`).
2. **SessionStart** records the start commit, pin status and a hash snapshot of every
   protected file (`session_start`), plus a bounded content-hash snapshot of the
   working-tree changes (`file_snapshot`). These are the baselines for tamper and
   file-change detection.
3. **PreToolUse** runs the tamper guard: writes/edits to protected paths (agent
   config, MCP config, `.aiproof/`, `.git/hooks/`) are *denied*. The attempt is
   logged as `tamper_attempt`.
4. **PostToolUse** logs the command and (truncated, redacted) output — this is the
   raw material the `tests_ran` check parses later.
5. **Stop** ("I'm done"): the final message is scanned for claims; each claim is run
   through the applicable checks; whole-session integrity checks run; the gate
   decides whether to block. Either way, a `gate_decision` record is written.
6. Everything written to the ledger is redacted first (`redact/`). The ledger is a
   hash chain, so later tampering is detectable (`ledger verify`).

## Pinned configuration (the trust anchor)

Gate-critical settings live in a **pinned** copy under `~/.aiproof/projects/<hash>/`
(`config.py: write_pinned`). The pinned record stores both the settings and a
SHA-256 of the canonical critical subset. On every gate evaluation the effective
settings are re-merged with the pinned copy (`merge_pinned`), so editing an in-repo
`aiproof.toml` cannot relax the gate. If the pin hash does not match, the gate treats
it as tampering.

Critical keys: `strictness`, `test_command`, `enabled_checks`, `protected_paths`,
`protect_ci`.

## Failure modes & guarantees

| Failure | Behaviour |
| --- | --- |
| AiProof code raises inside a hook | logged; exits 0 (fail-open) |
| Agent edits a protected file | PreToolUse denial (enforce) / recorded (observe) |
| Agent tampers with the ledger | `aiproof ledger verify` reports the first broken link |
| Secret appears in the diff | integrity check fails; the value is never written to disk |
| Pinned settings edited | hash mismatch → integrity finding |
| Tests claimed but not run | `tests_ran` fail (enforce) / unknown (observe) |

## Module reference

| Path | Responsibility |
| --- | --- |
| `paths.py` | every filesystem location; project hashing |
| `config.py` | layered settings + pinned gate config |
| `gitutil.py` | safe git plumbing |
| `ledger/` | hash-chained store, verify, receipts |
| `redact/` | secret patterns, entropy, redaction, scanning |
| `claims/` | claim model + multilingual extractor |
| `checks/` | per-claim and whole-session checks |
| `gate/` | block decision + localized messages |
| `guard/` | tamper guard + human-only actions |
| `adapters/` | agent/IDE registry + adapters |
| `hooks/` | lifecycle event entrypoints |
| `mcp/` | read-only MCP server |
| `maintenance/` | init/uninstall, doctor, pause, update |
| `bench/` | deterministic scenario harness |
| `i18n/` | catalogs + lookup |
| `tui/` | Rich dashboard |
| `cli.py` | command-line surface |
