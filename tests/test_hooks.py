"""Hook entrypoint: SessionStart records the file-snapshot baseline."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiproof.bench.harness import make_repo
from aiproof.hooks import entry
from aiproof.ledger.store import LedgerStore


def test_session_start_emits_file_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))
    root, _head = make_repo(tmp_path / "repo")
    (root / "notes.txt").write_text("hi\n", encoding="utf-8")  # untracked -> dirty
    payload = {"hook_event_name": "SessionStart", "session_id": "s1", "cwd": str(root)}
    monkeypatch.setattr(entry, "read_stdin", lambda: payload)

    assert entry.handle("SessionStart") == 0

    records = LedgerStore(root).records(session="s1")
    events = [r.get("event") for r in records]
    assert "session_start" in events
    assert "file_snapshot" in events

    snapshot = next(r for r in records if r.get("event") == "file_snapshot")
    assert "notes.txt" in snapshot["payload"]["files"]
