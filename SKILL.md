# SKILL: working with AiProof active

AiProof (`aiproof`) is a verification layer running alongside you. It is **offline** and
**read-only** with respect to your work: it never sends anything anywhere and never edits
your code. What it does is check whether your final claims are true against real evidence
(git, test output, the filesystem) and — via the agent's `Stop` hook — **block your "I'm
finished"** until they are.

You do not need to call AiProof. You need to **not lie to it**, because it will notice.

## Rules of engagement

1. **Do not edit AiProof's config or state.** Do not touch `.claude/settings*.json`,
   `.mcp.json`, `**/mcp.json`, `.aiproof/**`, `**/pinned.toml`, `**/ledger*.jsonl`, or the
   gate/hook scripts. The tamper guard denies these writes, and any change is re-detected at
   Stop. If you believe the config is wrong, say so — a human changes it.

2. **Never delete, skip or weaken tests to make them pass.** Deleting a test file, adding
   `skip`/`xfail`/`only`/`todo`/`#\[ignore\]`/`@Disabled`, or turning an exact assertion into
   a loose one is detected. If a test *should* be removed, **show the matching source
   removal in the same change** — a justified removal is allowed, an unexplained one is
   blocked.

3. **Phrase claims precisely.** Numbers, hashes and file names are checked.
   * Good: "12 tests passed", "committed as `9f2c1a4`", "created `src/app.py`".
   * Bad: "everything works", "all good", "fixed all tests".
   Hedged ("should pass") or negated ("not committed yet") statements are treated as *no
   claim* — they will not block you, but they will not count as progress either.

4. **Do not claim what you did not verify.** "All tests pass" is a claim; if no test command
   ran this session, it is a false claim and the gate will block. Run the tests, then report
   the exact counts from the output.

5. **Respect learned rules.** A repository may contain an `AGENTS.md` block (and compiled
   rules) recording corrections from the human, e.g. "do not mock the database in integration
   tests". These are enforced. Read the block between `<!-- aiproof:start -->` and
   `<!-- aiproof:end -->` and follow it.

## How to end a task honestly

1. Run the real commands (tests, build, lint) and read their output.
2. Report **exact** results: counts, the commit hash, the files you changed.
3. If something is unfinished, say so plainly. An honest "not done yet" never blocks you;
   a false "done" always does.
4. If the gate blocks you, **fix the specific problem it names** (it lists exact files and
   commands), then run the full test command and report the exact counts. It is designed so
   you can fix everything in one or two attempts; after a cap it records the forced stop.

## Self-check with MCP (optional)

If the host exposes AiProof over MCP, you can verify before claiming:

* `aiproof_verify_claims` — submit your claims text, get per-claim verdicts (no side effects).
* `aiproof_status` — armed state, pinned-config integrity, ledger status.
* `aiproof_scan_secrets` — check the diff for secrets (type + location + fingerprint only).
* `aiproof_corrections_list` — see the human's recorded corrections and compiled rules.

These are **read-only**. They help you; they cannot change anything. Use
`aiproof_verify_claims` when unsure whether a claim will hold.

## Receipt block (optional convention)

If asked, end with a machine-readable block listing claims and the commands you ran:

```
AIPROOF-RECEIPT
claims:
- tests_pass: 12
- committed: 9f2c1a4
commands:
- pytest -q
- git commit -m "fix auth"
END-AIPROOF-RECEIPT
```

AiProof parses this as **additional claims but never as evidence** — every line is still
verified against git and the real test output. A block that lies is caught exactly like a
prose lie. Use it to be *clearer*, never to be believed on faith.

## If AiProof itself breaks

It is **fail-open**: if it errors, it logs the error and lets you continue; the failure shows
up in `aiproof status` and `aiproof doctor`. You should still tell the human, because a
degraded verifier is not verifying.

## What AiProof is not

It is not a sandbox and not a security boundary. It reduces risk and enforces honesty about
*this session*. Do not treat a passing gate as proof the work is correct — only as proof that
your claims matched the evidence.
