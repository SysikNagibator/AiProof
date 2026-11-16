# Threat model

AiProof defends against an **adversarial coding agent** — or an agent that has been
manipulated (prompt injection, compromised tool, over-eager model) — that tries to
appear successful when it is not, or to disable/undermine verification.

We do **not** claim to defend against a malicious local user with root, nor against a
compromised kernel/OS. This is a developer-trust tool, not a sandbox against yourself.

## Assets

- The truth of what the agent actually did (git, tests, files).
- The user's secrets (tokens, keys, credentials).
- The integrity of AiProof's own configuration and history.

## Adversary capabilities we consider

| Capability | Example |
| --- | --- |
| Write/edit repo files | normal agent file tools |
| Run shell commands | `bash -c`, `sed -i`, redirection |
| Modify agent config | `.claude/settings.json`, `.mcp.json` |
| Delete/skip/weaken tests | remove a failing test, add `@skip` |
| Fabricate success | "all tests pass", "committed as …" |
| Try to disable AiProof | edit pins, pause, uninstall, rewrite the ledger |

## Defences and their limits

### 1. Deterministic claim verification (Stop)

Claims are matched with regexes against the *actual* git/test/filesystem state. An
agent cannot "talk its way" past a missing commit.

*Limit:* a claim phrased outside the supported patterns is not verified (it becomes
`unknown`, not a false `pass`). Supported languages are listed in [`CLAIMS.md`](CLAIMS.md).

### 2. Test-run parsing

A `tests_pass` claim passes only if a real test command ran this session and its parsed
counts do not contradict the claim. In `strict`, an unparsable run is `unknown` → blocks.

*Limit:* if the agent prints fake test output itself, we cannot distinguish it from a
real runner's output by text alone. Mitigation: prefer a real `test_command`, and treat
suspiciously clean output as `unknown` in `strict`.

### 3. Test-tamper detection

Deleted test files/cases, newly added `skip`/`xfail`/`only` markers, and exact matchers
replaced by loose ones are flagged.

*Limit:* renaming/refactoring tests legitimately can look like deletion; we allow it when
matching non-test source changes accompany it (see scenario 27/28 in [`BENCH.md`](BENCH.md)).

### 4. Secret redaction & scanning

Every value written to the ledger is redacted first (patterns + entropy). The diff and
agent instruction files are scanned for secrets (types/locations only).

*Limit:* no secret detector is complete. Redaction is best-effort and additive — we
also redact high-entropy strings near sensitive keywords.

### 5. Pinned configuration

Gate-critical settings are frozen with a self-hash and merged over any in-repo config.
Editing a repo config cannot relax the gate; editing the pin is detected.

*Limit:* an attacker with write access to `~/.aiproof/` can delete the pin; the gate then
reports the pin as missing and `doctor` surfaces it.

### 6. Tamper guard (PreToolUse)

Writes to protected paths are denied before they happen, and attempts are recorded.

*Limit:* only as strong as the agent's hook fidelity. In wrapper/MCP-only mode there is
no mid-session blocking, only post-hoc detection.

### 7. Hash-chained ledger

Records are chained; `ledger verify` reports the first altered link.

*Limit:* it detects tampering, it does not prevent it. Rotation is supported and the
chain continues across segments.

### 8. Human-only disarm

`pause`, `resume`, `pin` and `uninstall` require an interactive human TTY (and refuse in
CI). An agent running hooks cannot disarm the gate.

## Trust boundaries

- **In-repo files** are untrusted input (the agent can write them).
- **`~/.aiproof/`** is the trust anchor (pins, ledger). Prefer it outside the repo.
- **The agent's final message** is untrusted input.

## Non-goals

- Sandboxing the agent or its shell.
- Detecting a genuinely correct-but-unusual solution (we only check claims).
- Network/cloud monitoring. AiProof has none.
