# Why AiProof exists

## The problem

Large language model agents are relentlessly optimistic. Ask one to fix a bug and it
will very often end with something like:

> "Done! All tests pass, I committed the fix as `9f2c1a4`."

And a surprising fraction of the time, none of that is true:

- the tests were never run (or were run in the wrong directory, or filtered to nothing);
- the "commit" does not exist, or lives on another branch;
- a failing test was quietly deleted, skipped, or had its assertion loosened;
- a secret leaked into the diff;
- a `TODO` was removed rather than done.

You cannot fix this with a better prompt. The agent's summary is a *claim*, and claims
need *evidence*. Developers already know this: we trust tests, not assurances.

## The idea

**AiProof treats the agent's final message as a set of claims and verifies each claim
against local, deterministic evidence.** When a claim cannot be backed by evidence,
AiProof can stop the agent's "done" and tell it exactly what is wrong.

This reframes the problem from *"make the model more honest"* (hard, probabilistic) to
*"check the receipts"* (easy, deterministic). It is the same shift as moving from
"trust the vendor's changelog" to "reproduce it in CI".

## Principles

- **Evidence over vibes.** A verdict is `pass`, `fail`, or `unknown` — never a silent
  pass. `unknown` is honest, not a failure of nerve.
- **Local and private.** Your code and secrets never leave the machine. The ledger is
  redacted and stored under `~/.aiproof/`.
- **Deterministic.** No model in the verification loop. The same inputs give the same
  verdict, every time.
- **Layered defence.** Mid-session blocking (hooks) where available, then post-hoc
  verification (wrapper/MCP) everywhere else. See [`AGENTS_SUPPORT.md`](AGENTS_SUPPORT.md).
- **Honest about limits.** We document what we cannot catch (see [`BENCH.md`](BENCH.md))
  instead of hiding misses.

## What "done" means now

```
Agent: "Done! All tests pass and I committed the fix."
AiProof: nothing.
   ...later, if the evidence disagrees...
AiProof: "You claimed the tests pass, but no test command was run this session;
          you claimed a commit, but no matching commit exists."
```

That single intervention is the whole point.
