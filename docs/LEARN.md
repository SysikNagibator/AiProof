# Learning (Phase 2)

Phase 2 is the differentiator: a human correction can become an **executable check** that
blocks the repeated mistake in future sessions. This page documents the whole pipeline and
its honest limits.

## Pipeline

```
aiproof correct "<text>"
        │  recorded in the ledger (redacted, de-duplicated)
        ▼
aiproof learn compile --write
        │  matching corrections become DISABLED rules in rules.toml
        ▼
aiproof learn backtest <rule-id>
        │  replay over local history + recorded commands
        ▼
aiproof learn enable <rule-id>          (human-only, interactive TTY)
        │
        ▼
gate: learn_rules integrity check       (blocks on a matching enabled rule)
        │
        ▼
aiproof learn export                    (writes the AGENTS.md marker block)
```

## 1. Record a correction

```sh
aiproof correct "Do not mock the database in integration tests"
aiproof correct "never run \`git push --force\`"
aiproof correct "never import django in src/**/*.py"
```

Corrections are stored in the ledger as `correction` events, so they pass through the
redactor first — a secret inside a correction is redacted before it reaches disk and can
never leak into a rule. Duplicates (case- and whitespace-insensitive) are ignored. Each
correction gets a stable id (`C001`, `C002`, …) and a cosmetic topic.

## 2. Compile to a rule

```sh
aiproof learn compile          # preview
aiproof learn compile --write  # persist (rules start DISABLED)
```

Compilation is intentionally conservative. Only a small set of unambiguous templates is
compiled; everything else stays **advisory** and is labelled "not enforced" everywhere.

Compiled templates:

| template | example correction | produced rule |
| --- | --- | --- |
| test-style | "do not mock the database in integration tests" | `no-db-mock-in-integration` (`scope = tests/integration/**/*.py`) |
| import | "never import django in src/**/*.py" | `no-import-django` |
| command | "never run `git push --force`" | `no-command-git-push-force` |
| path lock | "never edit .github/workflows/ci.yml" | `no-edit-...` |

A rule is declarative TOML:

```toml
[rule.no-db-mock-in-integration]
description = "Do not mock the database in integration tests"
scope = "tests/integration/**/*.py"
forbid_added_regex = ['(?i)mock\.patch\(.*(db|session|engine)']
severity = "block"
enabled = false
source_correction = "C014"
```

The DSL (`src/aiproof/learn/dsl.py`) supports: `scope` (git-style glob with `**`/`*`/`?`),
`forbid_added_regex`, `require_added_regex`, `forbid_command_regex`, `severity`
(`block`/`warn`) and `enabled`. Rules are validated on load and save; a malformed regex or
severity is rejected (`RuleError`) rather than silently applied.

A line carrying `aiproof:ignore` is a **waiver**: it is not a hit, and the backtester counts
it as a false positive (an intentional, documented exception).

## 3. Backtest before enabling

```sh
aiproof learn backtest no-db-mock-in-integration
```

The backtester replays the rule over the last ~200 non-merge commits (added lines parsed
from `git show --unified=0`) plus every command recorded in the ledger, and reports:

* `commits_scanned`
* `would_have_caught` — commits/commands where the rule matched
* `false_positives` — matches that carried an `aiproof:ignore` waiver
* up to 5 sample hits (redacted)

**Honest limit:** without labelled history we cannot know a *true* false-positive rate.
`false_positives` is a **lower bound** (explicit waivers only). The result carries a note
saying exactly this. Do not present the number as a precision.

A rule with a high `would_have_caught` and low `false_positives` is a good candidate; enable
it only after you have looked at the samples.

## 4. Enable / disable (human only)

```sh
aiproof learn enable  no-db-mock-in-integration
aiproof learn disable no-db-mock-in-integration
```

These require an interactive human terminal (`AIPROOF_NON_INTERACTIVE=1` or `CI` refuses),
and each toggle writes a `rule_toggle` ledger event. Only enabled rules are enforced.

## 5. Enforcement

The `learn_rules` integrity check (`src/aiproof/checks/learn_rules.py`) collects the added
lines per changed/untracked file since session start plus the session's observed commands,
then runs every enabled rule. A `block` rule that matches yields a `fail` finding; a `warn`
rule yields `unknown`. The gate's `decide()` considers these findings and the message
surfaces the rule id, description and sample locations. See `docs/CHECKS.md`.

This is proven by **benchmark scenario 31**: a recorded correction compiled to an enabled
rule blocks the repeated mistake.

## 6. Export to `AGENTS.md`

```sh
aiproof learn export                 # default target AGENTS.md
aiproof learn export --target CLAUDE.md
```

Writes only the block between the markers, never touching user text:

```markdown
<!-- aiproof:start -->
## AiProof rules (enforced)

These rules are enforced by AiProof. Follow them in this repository.

- **no-db-mock-in-integration** (block) — Do not mock the database in integration tests
  - scope: `tests/integration/**/*.py`

_Generated by AiProof. Edit only outside the marker comments._
<!-- aiproof:end -->
```

The block lists **only enabled rules**; a re-run is idempotent (no change → `unchanged`), and
an existing file is backed up as `*.bak` before rewrite. Because corrections are redacted
before storage, secrets cannot leak into the block.

## What is not enforced

Corrections that do not match a template stay **advisory text**. They are shown in
`aiproof learn` and the TUI's Rules & Corrections screen with the label "advisory (not
enforced)" and never affect the gate.

## Effectiveness

Rule hits accrue as `learn_rules` findings in the ledger, so a dashboard can show "repeat
mistakes this week vs before" by counting findings per rule over time. `aiproof watch`
streams the same events live.
