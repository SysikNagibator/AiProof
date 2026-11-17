# Benchmark

`aiproof bench` is the proof that AiProof works. It is **deterministic and uses no real
LLM**: scripted fake-agent transcripts run against small fixture repos created in a temp
directory. The same input always yields the same verdicts.

## Output

```sh
aiproof bench          # rich table
aiproof bench --json   # machine-readable
aiproof bench --md     # markdown table for the README
```

Each row: scenario, expected verdict, AiProof verdict, caught/missed, false positive, time
(ms). Totals at the bottom: detection rate, false-positive rate, median hook latency.

The README table and `docs/BENCH_RESULTS.md` are **generated** from `aiproof bench --md`;
never hand-edit them.

## The 31 scenarios

1–24 are false-claim/tamper/security scenarios (deleted tests, weakened assertions,
hardcoded lookup table, fake commits, wrong branch, unchanged "written" file, count
mismatch, tests never run, wrong directory, empty filter, secrets in diff / instruction
file / untracked file, hook-config edit, MCP-config edit, AiProof-config edit, deleted
TODOs, shell obfuscation, non-interactive pause/pin, ledger tampering, multilingual false
claims).

25–29 are the **false-positive** and honesty scenarios: hedged/negated statements that must
*not* be treated as false claims, an honest successful run, a legitimate test removal with
matching source removal, a legitimate test rename refactor, and a large monorepo latency
fixture.

30 is the gate-cap behavior: repeated blocks then a recorded forced stop.

31 is the Phase 2 proof: a recorded correction compiled to an enabled rule blocks the
repeated mistake (see `docs/LEARN.md`).

Scenario 5 (hardcoded lookup table replacing logic) is a heuristic and is the one
**documented miss** — it is listed under "Known gaps", never hidden.

## Current numbers

Detection rate **96%** (25/26 positives; the miss is scenario 5), false-positive rate
**0%** (all 5 negatives correctly allowed), median hook latency **~55–80 ms**
(host-dependent).

These are real numbers produced on the development machine by the command below. Latency
varies by host; detection and false-positive rates do not.

```sh
aiproof bench --md > docs/BENCH_RESULTS.md
```

## Adding a scenario

1. Add a function `sNN(tmp) -> (blocked, expected_block, note)` in
   `src/aiproof/bench/scenarios/__init__.py`.
2. Register it in `SCENARIOS`.
3. Update the count assertions in `tests/test_bench.py`.
4. Regenerate `docs/BENCH_RESULTS.md`.

If a new scenario reveals a miss, add it to "Known gaps" in the README rather than
tuning it into a pass. An honest miss is worth more than a fake number.
