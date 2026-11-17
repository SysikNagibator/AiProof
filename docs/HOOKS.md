# Hooks

AiProof integrates with an agent through that agent's **lifecycle hooks**. A hook is
a short-lived process the agent spawns at a defined moment and whose output the agent
interprets. AiProof never patches the agent and never talks to it over the network.

## Contract

Every hook entrypoint obeys the same contract:

* **Fail-open.** If AiProof raises, times out, or cannot parse its input, it logs the
  failure and exits `0`. An internal error must never brick the agent. The failure is
  surfaced in `aiproof status` and `aiproof doctor` as *degraded*.
* **Fast.** The hook budget is ~150 ms p95 (see `docs/BENCH.md`). Hooks read only local
  state; there is no network I/O on the hot path.
* **Silent unless needed.** A hook prints nothing when there is nothing to report. The
  agent's stdout is reserved for the JSON decision object.
* **Redacted.** Anything a hook writes to the ledger passes through the redactor first
  (see `docs/LEDGER.md`).

The entrypoint is a single command: `aiproof hook <EventName>`. It reads the agent's
JSON payload from stdin and writes at most one JSON object to stdout.

Exit codes:

| code | meaning |
| --- | --- |
| `0` | success (may carry a JSON decision on stdout) |
| `2` | usage error (only when invoked by hand without an event name) |

## Claude Code (verified)

Verified against the current Claude Code hooks reference and guide on **2026-11-16**.
This is the only integration whose event names, stdin schema and decision schema have
been checked against vendor documentation.

Events AiProof registers (`src/aiproof/adapters/claude_code.py`):

| event | matcher | purpose |
| --- | --- | --- |
| `SessionStart` | — | record `session_start` (start commit + protected files) and `file_snapshot` |
| `PreToolUse` | `Bash\|Edit\|Write\|MultiEdit\|NotebookEdit` | tamper guard; record `tool_pre` |
| `PostToolUse` | `Bash\|Edit\|Write\|MultiEdit\|NotebookEdit` | record `tool_post` (command + truncated output) |
| `Stop` | — | extract claims, run checks, block on a false claim |

The hook block is merged into the agent's settings file, marker-delimited so a re-run
is idempotent and `aiproof uninstall` removes only AiProof's own entries. Locations:

* project: `.claude/settings.json`
* local (gitignored): `.claude/settings.local.json`
* user (opt-in): `~/.claude/settings.json`

Choose the level with `aiproof init --level project|local|user`. Existing user entries
are preserved; AiProof only adds or replaces the entries that carry its marker.

### `Stop` block schema

AiProof emits the documented Stop decision object:

```json
{ "decision": "block", "reason": "AiProof: you claimed 42 tests pass ..." }
```

It honors the documented `stop_hook_active` field and caps consecutive blocks at
`MAX_BLOCKS = 2` (`src/aiproof/hooks/entry.py`). After the cap, it stops blocking, records
a `gate_decision` with `"capped": true`, and surfaces the capped state loudly in `status`
and in the receipt. The goal is that an agent can fix everything in one or two attempts.

### `PreToolUse` deny schema

The tamper guard returns a deny decision for writes to protected paths:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "AiProof protects .claude/settings.json ..."
  }
}
```

Deny lists are **risk reduction, not a security boundary**. A determined agent with
shell access can defeat string heuristics; that is why the pinned-config integrity check
(`config_integrity`) re-verifies the protected files at `Stop`.

## Other agents

Every other agent in `src/aiproof/adapters/registry.py` is marked `planned` or
`unverified`. We do **not** invent their hook APIs. Two integration tiers exist for them:

* **`mcp-only`** — the agent connects to `aiproof mcp` and can *ask* AiProof to verify
  claims, but cannot be blocked mid-session (no lifecycle hook is used).
* **`wrapper`** — `aiproof run -- <agent> ...` verifies *after* the process exits. This is
  post-hoc and cannot block.

See `docs/AGENTS_SUPPORT.md` for the current per-agent status and the exact date each
verified integration was checked. The honesty rule from the spec is enforced by review:
`status = verified` requires a recorded verification date.

## Testing hooks

`tests/test_hooks.py` spawns the real entrypoints with realistic stdin payloads and
asserts exit codes and JSON output. You can do the same by hand:

```sh
echo '{"session_id":"s1","cwd":"'$PWD'","last_assistant_message":"all tests pass"}' \
  | aiproof hook Stop
```

`AIPROOF_TEST_MESSAGE` overrides the transcript so you can simulate a claim without an
agent. `AIPROOF_DISABLE=1` is the documented emergency kill switch: the hook logs that it
was skipped and exits `0`.

## Reproducing the verification

The Claude Code contract was checked against these pages on 2026-11-16: the *Hooks* guide,
the *Hooks reference* (event list, matchers, stdin schema, exit codes, JSON decisions),
and the `stop_hook_active` re-entrancy note. If a vendor changes the contract, update
`docs/AGENTS_SUPPORT.md`, bump the verification date, and adjust
`src/aiproof/adapters/claude_code.py` — never guess.
