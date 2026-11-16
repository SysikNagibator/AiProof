"""Per-project ledger store: append, rotate, read back."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

from aiproof import paths
from aiproof.ledger import chain
from aiproof.ledger._lock import file_lock

ROTATE_BYTES = 8 * 1024 * 1024
Redactor = Callable[[Any], Any]


def segment_paths(root: Path) -> list[Path]:
    """Return ledger segment files for a project in chain order (oldest first)."""
    directory = paths.project_dir(root)
    if not directory.is_dir():
        return []
    segments = [p for p in directory.glob("ledger*.jsonl") if p.is_file()]

    def sort_key(p: Path) -> tuple[int, str]:
        # "ledger.jsonl" is the active (newest) segment; numbered ones come first.
        name = p.name
        if name == "ledger.jsonl":
            return (1_000_000, name)
        middle = name[len("ledger.") : -len(".jsonl")]
        try:
            return (int(middle), name)
        except ValueError:
            return (999_999, name)

    return sorted(segments, key=sort_key)


def read_records(root: Path) -> Iterator[tuple[Path, int, dict[str, Any]]]:
    """Yield ``(segment, 1-based line, record)`` across every segment in order."""
    for segment in segment_paths(root):
        try:
            text = segment.read_text(encoding="utf-8")
        except OSError:  # pragma: no cover - unreadable segment
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            yield segment, lineno, chain.parse_line(stripped)


def _tail(path: Path) -> tuple[str, int]:
    """Return ``(prev_hash, last_seq)`` for the last record in *path*."""
    if not path.is_file() or path.stat().st_size == 0:
        return chain.GENESIS, 0
    last = ""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last = line
    if not last:
        return chain.GENESIS, 0
    record = chain.parse_line(last)
    prev = record.get("hash")
    seq = record.get("seq")
    if not isinstance(prev, str) or not isinstance(seq, int):
        return chain.GENESIS, 0
    return prev, seq


class LedgerStore:
    """Append-only store; safe for many short-lived hook processes."""

    def __init__(
        self,
        root: Path,
        *,
        redact: Redactor | None = None,
        rotate_bytes: int = ROTATE_BYTES,
    ) -> None:
        self.root = paths.canonical_path(root)
        self.dir = paths.project_dir(self.root)
        self._redact = redact
        self._rotate_bytes = rotate_bytes

    # -- helpers ---------------------------------------------------------- #
    def _ensure(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        meta = paths.project_meta_path(self.root)
        if not meta.is_file():
            payload = {
                "path": os.fspath(self.root),
                "hash": paths.project_hash(self.root),
                "created": chain.now_iso(),
            }
            meta.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _redact_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._redact is not None:
            result = self._redact(payload)
            if isinstance(result, dict):
                return result
            return {"redacted": result}
        from aiproof.redact.redactor import redact_json

        return cast("dict[str, Any]", redact_json(payload))

    def _maybe_rotate(self, active: Path) -> None:
        if not active.is_file() or active.stat().st_size < self._rotate_bytes:
            return
        index = 1
        while (self.dir / f"ledger.{index:04d}.jsonl").exists():
            index += 1
        active.rename(self.dir / f"ledger.{index:04d}.jsonl")

    # -- public API ------------------------------------------------------- #
    def append(self, event: str, payload: dict[str, Any], *, session: str) -> dict[str, Any]:
        """Append one redacted, hash-chained record and return it."""
        self._ensure()
        active = paths.ledger_path(self.root)
        lock = self.dir / ".ledger.lock"
        with file_lock(lock):
            # Read the chain tail *before* rotating so the new segment continues
            # the chain instead of restarting at GENESIS.
            segments = segment_paths(self.root)
            if segments:
                prev, last_seq = _tail(segments[-1])
            else:
                prev, last_seq = chain.GENESIS, 0
            self._maybe_rotate(active)
            safe = self._redact_payload(payload)
            record = chain.make_record(
                session=session,
                seq=last_seq + 1,
                event=event,
                payload=safe,
                prev=prev,
            )
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
            with active.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
            return record

    def head(self) -> str:
        """Return the current chain head hash (``GENESIS`` when empty)."""
        segments = segment_paths(self.root)
        if not segments:
            return chain.GENESIS
        prev, _ = _tail(segments[-1])
        return prev

    def records(self, *, session: str | None = None) -> list[dict[str, Any]]:
        """Return every record, optionally filtered by session id."""
        out: list[dict[str, Any]] = []
        for _segment, _lineno, record in read_records(self.root):
            if session is None or record.get("session") == session:
                out.append(record)
        return out

    def last_session(self) -> str | None:
        """Return the session id of the most recent record."""
        last: str | None = None
        for _segment, _lineno, record in read_records(self.root):
            sid = record.get("session")
            if isinstance(sid, str):
                last = sid
        return last
