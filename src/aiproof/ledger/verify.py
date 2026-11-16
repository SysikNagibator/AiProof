"""Ledger chain verification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aiproof.ledger import chain, store


@dataclass(slots=True)
class VerifyResult:
    """Outcome of a chain verification pass."""

    ok: bool
    checked: int
    segments: int
    head: str
    first_broken_seq: int | None = None
    reason: str = ""

    def summary(self) -> str:
        """Human-readable one-line summary."""
        if self.ok:
            return f"chain OK: {self.checked} records across {self.segments} segment(s)"
        return f"chain BROKEN at seq {self.first_broken_seq}: {self.reason}"


def verify(root: Path) -> VerifyResult:
    """Recompute the hash chain for *root* and report the first broken link."""
    segments = store.segment_paths(root)
    prev = chain.GENESIS
    checked = 0
    head = chain.GENESIS
    for _segment, _lineno, record in store.read_records(root):
        expected_prev = record.get("prev")
        if expected_prev != prev:
            return VerifyResult(
                False,
                checked,
                len(segments),
                head,
                record.get("seq"),
                "prev hash does not match the previous record",
            )
        meta = chain.record_meta(record)
        recomputed = chain.record_hash(prev, meta)
        if recomputed != record.get("hash"):
            return VerifyResult(
                False,
                checked,
                len(segments),
                head,
                record.get("seq"),
                "record hash mismatch (content altered)",
            )
        prev = recomputed
        head = recomputed
        checked += 1
    return VerifyResult(True, checked, len(segments), head)
