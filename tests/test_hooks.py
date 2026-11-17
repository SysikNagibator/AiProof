"""Hook entrypoint: SessionStart records the file-snapshot baseline."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from aiproof import paths
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


def test_stop_respects_pause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A human pause must stop the Stop hook from blocking false claims."""
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))
    root, _head = make_repo(tmp_path / "repo")
    state = paths.project_dir(root) / "state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"paused_until": int(time.time()) + 600}), encoding="utf-8")
    payload = {
        "hook_event_name": "Stop",
        "session_id": "s1",
        "cwd": str(root),
        "last_assistant_message": "Created the file missing.py.",
    }
    monkeypatch.setattr(entry, "read_stdin", lambda: payload)

    assert entry.handle("Stop") == 0

    decisions = [
        r["payload"]
        for r in LedgerStore(root).records(session="s1")
        if r.get("event") == "gate_decision"
    ]
    assert decisions and decisions[-1]["block"] is False
    assert decisions[-1]["paused"] is True
