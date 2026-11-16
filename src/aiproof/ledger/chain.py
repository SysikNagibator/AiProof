"""Append-only, hash-chained JSONL ledger primitives."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

LEDGER_VERSION = 1
GENESIS = "0" * 64


def canonical_json(obj: Any) -> str:
    """Return a stable canonical JSON string used for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def record_meta(record: dict[str, Any]) -> dict[str, Any]:
    """Return the hashable portion of a record (everything but ``prev``/``hash``)."""
    return {k: v for k, v in record.items() if k not in ("prev", "hash")}


def record_hash(prev: str, meta: dict[str, Any]) -> str:
    """Compute ``sha256(prev + canonical_json(meta))``."""
    payload = (prev + canonical_json(meta)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def make_record(
    *,
    session: str,
    seq: int,
    event: str,
    payload: dict[str, Any],
    prev: str,
    ts: str | None = None,
) -> dict[str, Any]:
    """Build a complete ledger record with its chained hash."""
    meta: dict[str, Any] = {
        "v": LEDGER_VERSION,
        "ts": ts or now_iso(),
        "session": session,
        "seq": seq,
        "event": event,
        "payload": payload,
    }
    digest = record_hash(prev, meta)
    return {**meta, "prev": prev, "hash": digest}


def parse_line(line: str) -> dict[str, Any]:
    """Parse one JSONL line into a record; raises ``ValueError`` when malformed."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"invalid ledger line: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("ledger record is not an object")
    return obj
