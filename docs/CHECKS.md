# Checks

A **check** tries to falsify one thing. Every check returns a verdict plus structured
evidence: `pass`, `fail`, or `unknown`. `unknown` is never turned into `pass`.

Two families live in `src/aiproof/checks/`:

* **claim checks** — bound to a `Claim` (`applies(claim)` + `check(claim, ctx)`), registered
  in `CLAIM_CHECKS`.
* **integrity checks** — whole-session (`run(ctx) -> list[IntegrityFinding]`), registered
  in `INTEGRITY_CHECKS`.

`CheckContext` gives a check everything it may read: `root`, `settings`, `session`,
`start_commit`, `records` (ledger events), `claims`, plus `commands()` and `events()` helpers.
All state is local and deterministic.

## Claim checks

### `commit_exists`
A claimed hash (or "I committed") is verified in the git object store. The commit must
exist, be reachable from HEAD (an ancestor of the current branch), and — when files are
claimed — touch them. A missing object, a detached/other-branch commit, or a commit that
does not touch the claimed files is a `fail`.

### `file_changed`
Claimed files must actually differ from the session-start snapshot in the ledger
(`file_snapshot` event, content hashes). "Claimed but identical" is a `fail`. The snapshot
is authoritative for files that were already modified or untracked at `session_start`, so a
file left untouched cannot pass merely because it differs from HEAD. Files absent from the
snapshot fall back to git plumbing (`git status`, the start commit); when neither yields
evidence the claim is a `fail`. A claim that names no file is `unknown`.

### `tests_ran`
The project's test command must really have run in this session, evidenced by a
`tool_post` event whose command matches a known runner (pytest, unittest, jest, vitest,
mocha, go test, cargo test, rspec, phpunit, …). AiProof parses real counts from the
captured output and compares them to the claim ("42 passed" vs 31). It also detects
wrong-directory runs and filters that matched zero tests (`collected 0 items`,
`no tests ran`). No run → `fail`/`unknown` depending on strictness.

## Integrity checks

### `test_tamper`
Compares test files at `session_start` vs now. Flags: deleted test files; removed test
definitions (`def test_...`, `it(`, `test(`, ...); new
`skip`/`xfail`/`only`/`todo`/`#\[ignore\]`/`@Disabled` markers; and weakening an exact
matcher (`toBe(x)`, `assertEqual(a, b)`) to a zero-argument truthy matcher. It does **not**
count assertions, detect removed `expect(...)` calls, or catch a hardcoded lookup table —
that is scenario 5, the single documented bench miss. A test removal is *justified* only
when a non-test source file was **deleted** in the same diff (not merely edited or added);
this heuristic avoids false positives on legitimate cleanup, and it remains bypassable by
deleting an unrelated source file, as documented in `docs/THREAT_MODEL.md`.

### `secrets_in_diff`
Scans staged + unstaged + untracked changes and the known instruction files for secret
formats. Reports only type + location + fingerprint, never the value. See
`docs/THREAT_MODEL.md` and the redactor notes below.

### `todo_integrity`
Detects open task/todo lines that were *deleted* rather than *completed* since session
start (deleted `TODO/FIXME/XXX/HACK` lines with no matching added-and-done task).

### `config_integrity`
Hashes the protected files (hook configs, MCP configs, AiProof's own config) at
`session_start` and re-verifies at `Stop`. Any change not made by the human is a finding.
It also re-verifies the pinned-config digest.

### `learn_rules`
Evaluates enabled rules compiled from human corrections (Phase 2, see `docs/LEARN.md`)
against the diff (added lines per file) and the session's observed commands. A rule with
`severity = "block"` that matches yields a `fail`; a `warn` rule yields `unknown`. No
enabled rules → no findings. A line carrying `aiproof:ignore` is a waiver and is not a hit
(presence of an intentional waiver is treated as a false positive in backtests).

## Strictness presets

| preset | unknown | confirmed fail | secrets/tamper |
| --- | --- | --- | --- |
| `observe` | log | log | log |
| `warn` | inject guidance | inject guidance | inject guidance |
| `enforce` (default) | record | **block** | **block** |
| `strict` | **block** on key claims | **block** | **block** |

The gate also blocks on a pinned-config mismatch at any strictness that blocks at all.

## Registry

`src/aiproof/checks/__init__.py`:

```python
CLAIM_CHECKS = (commit_exists, file_changed, tests_ran)
INTEGRITY_CHECKS = (test_tamper, secrets_in_diff, todo_integrity, config_integrity, learn_rules)
```

`DEFAULT_CHECKS` in `config.py` lists all of them; a subset can be toggled with
`aiproof checks` (human-only, writes the pinned copy).

## Adding a check

1. Create `src/aiproof/checks/<name>.py`.
2. Define `NAME`, and either the claim-check pair or `run(ctx)`.
3. Register it in `checks/__init__.py` and add it to `DEFAULT_CHECKS`.
4. Add positive, negative, edge and (where paths are involved) Windows-path cases to
   `tests/test_checks.py`.

Rule: never return `pass` on an error and never convert `unknown` to `pass`. If a check
cannot decide, it returns `unknown` with a reason.
