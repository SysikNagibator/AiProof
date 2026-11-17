# Ledger

The ledger is AiProof's tamper-evident record of what happened in a session. It is the
evidence base for every receipt and for the rule backtester. It is **append-only** and
**hash-chained**.

## Location and layout

```
~/.aiproof/projects/<project_hash>/
  project.json      # human-readable alias + full canonical digest
  pinned.toml       # gate-critical settings (human-pinned)
  ledger.jsonl      # active segment
  ledger.N.jsonl    # rotated segments, oldest first
  rules.toml        # compiled correction rules (Phase 2)
  state.json        # pause/resume state
  allow.toml        # secrets allowlist (project copy)
  receipts/         # exported receipts
  key               # optional HMAC key, 0600
```

`project_hash` is the SHA-256 of the **canonical** git top-level path (or cwd when not a
repo), truncated to 16 hex chars for a readable directory name; the full digest is stored
in `project.json` for integrity. `paths.py` is the single source of truth for every path.

## Record format

One JSON object per line (`src/aiproof/ledger/chain.py`):

```json
{
  "v": 1,
  "ts": "2026-11-16T18:32:05+00:00",
  "session": "s1",
  "seq": 7,
  "event": "gate_decision",
  "payload": { "...": "..." },
  "prev": "<64-hex>",
  "hash": "<64-hex>"
}
```

`hash = sha256(prev + canonical_json(record_minus_{prev,hash}))`. `prev` for the first
record is the genesis value (`"0" * 64`). Rotation happens at 8 MB; the chain continues
across segments (the first record of a new segment points at the last hash of the old one),
so `ledger verify` walks all segments in order.

## Event types

Emitted today: `session_start`, `tool_pre`, `tool_post`, `file_snapshot`,
`claims_extracted`, `check_result`, `gate_decision`, `tamper_attempt`, `correction`,
`rule_toggle`, `pause`, `resume`.

Reserved (readers accept them, but no code path emits them yet): `user_prompt`
(redacted, off by default), `test_run`, `secret_found`, `rule_hit`, `internal_error`.
`secret_found` findings currently travel inside `check_result`/`gate_decision`.

## Redaction before writing

Every payload passes through the redactor **before** it is hashed and written
(`LedgerStore` wraps a redactor). Consequences:

* Raw secrets never reach disk. `tests/test_ledger.py` asserts this directly.
* Full file contents are never stored — only hashes, sizes, line counts and bounded
  excerpts/diffs.
* The redaction placeholder is stable within a project (`[REDACTED:<type>:<4-hex>]`), so
  the same secret maps to the same token for diagnostics without being reversible.

## Verification

`aiproof ledger verify` recomputes the chain and reports the first broken link:

```
chain OK: 412 records across 1 segment(s)
```

or

```
chain BROKEN at seq 133: prev mismatch
```

`VerifyResult` carries `ok`, `checked`, `segments`, `head`, `first_broken_seq`, `reason`.

## Where it can be attacked (honest limits)

A plain hash chain prevents *silent* edits: changing any record breaks every later hash,
and an attacker who edits one record must also recompute all following hashes. That is
**detection of tampering**, not **prevention**.

An HMAC key (OS keychain via `keyring`, else `~/.aiproof/key` with `0600`) is **planned but
not implemented yet**; `paths.key_path()` is reserved for it. Treat the current chain as an
unkeyed SHA-256 chain. If an HMAC is added later it will still not be a cryptographic
signature of authorship: an attacker with the key and the ledger could forge it.

Ed25519 receipt signatures are a reserved `[sign]` extra and are **not implemented yet**
(see `docs/SIGNING.md`). When implemented they will sign the chain head, not each record.

## Receipts

`aiproof show <session> --format json|html|md` (alias `aiproof receipt`) builds a receipt
from the ledger: claims vs evidence, verdicts, tamper events, secret finding counts and the
chain head hash. JSON is machine-readable; HTML is self-contained, dark/light aware and
printable; MD is for pasting. The README badge snippet is generated from the same data.
