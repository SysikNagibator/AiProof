"""Hook events: PreToolUse, PostToolUse, SessionStart, Stop and fail-open paths."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from aiproof import paths
from aiproof.bench.harness import make_repo
from aiproof.hooks import entry
from aiproof.ledger.store import LedgerStore


def _payload(root: Path, event: str, **extra: object) -> dict[str, object]:
    return {"hook_event_name": event, "session_id": "s1", "cwd": str(root), **extra}


def _records(root: Path) -> list[dict[str, object]]:
    return LedgerStore(root).records(session="s1")


@pytest.fixture()
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AIPROOF_LANG", "en")
    monkeypatch.delenv("AIPROOF_DISABLE", raising=False)
    return tmp_path


# --------------------------------------------------------------------------- #
# stdin parsing
# --------------------------------------------------------------------------- #
def test_read_stdin_parses_and_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO('{"a": 1}'))
    assert entry.read_stdin() == {"a": 1}

    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert entry.read_stdin() == {}

    monkeypatch.setattr("sys.stdin", io.StringIO("[1, 2]"))
    assert entry.read_stdin() == {}

    monkeypatch.setattr("sys.stdin", io.StringIO("   "))
    assert entry.read_stdin() == {}

    class Broken:
        def read(self) -> str:
            raise OSError("closed")

    monkeypatch.setattr("sys.stdin", Broken())
    assert entry.read_stdin() == {}


def test_emit_writes_json(capsys: pytest.CaptureFixture[str]) -> None:
    entry._emit({"decision": "block"})
    assert json.loads(capsys.readouterr().out) == {"decision": "block"}
    entry._emit({})
    assert capsys.readouterr().out == ""


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
def test_disabled_short_circuits(isolated: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPROOF_DISABLE", "1")
    root, _ = make_repo(isolated / "repo")
    monkeypatch.setattr(entry, "read_stdin", lambda: _payload(root, "PreToolUse"))
    assert entry.handle("PreToolUse") == 0
    assert _records(root) == []


def test_pretooluse_denies_protected_write(
    isolated: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _ = make_repo(isolated / "repo")
    payload = _payload(
        root,
        "PreToolUse",
        tool_name="Bash",
        tool_input={"command": "rm .mcp.json"},
    )
    monkeypatch.setattr(entry, "read_stdin", lambda: payload)
    assert entry.handle("PreToolUse") == 0

    emitted = json.loads(capsys.readouterr().out)
    assert emitted["hookSpecificOutput"]["permissionDecision"] == "deny"
    records = _records(root)
    assert records[-1]["event"] == "tamper_attempt"
    assert ".mcp.json" in str(records[-1]["payload"])


def test_pretooluse_allows_safe_command(
    isolated: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _ = make_repo(isolated / "repo")
    payload = _payload(root, "PreToolUse", tool_name="Bash", tool_input={"command": "ls -la"})
    monkeypatch.setattr(entry, "read_stdin", lambda: payload)
    assert entry.handle("PreToolUse") == 0
    assert capsys.readouterr().out == ""
    assert _records(root)[-1]["event"] == "tool_pre"


def test_posttooluse_records_truncated_output(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = make_repo(isolated / "repo")
    payload = _payload(
        root,
        "PostToolUse",
        tool_name="Bash",
        tool_input={"command": "pytest -q"},
        tool_response="x" * (entry.OUTPUT_LIMIT + 500),
    )
    monkeypatch.setattr(entry, "read_stdin", lambda: payload)
    assert entry.handle("PostToolUse") == 0
    record = _records(root)[-1]
    assert record["event"] == "tool_post"
    payload_data = record["payload"]
    assert isinstance(payload_data, dict)
    assert len(str(payload_data["output"])) <= entry.OUTPUT_LIMIT


def test_session_start_snapshot(isolated: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _ = make_repo(isolated / "repo")
    (root / "notes.txt").write_text("hi\n", encoding="utf-8")
    monkeypatch.setattr(
        entry, "read_stdin", lambda: _payload(root, "SessionStart", source="startup")
    )
    assert entry.handle("SessionStart") == 0
    events = [record["event"] for record in _records(root)]
    assert "session_start" in events and "file_snapshot" in events
    start = next(r for r in _records(root) if r["event"] == "session_start")
    payload = start["payload"]
    assert isinstance(payload, dict)
    assert payload["source"] == "startup"
    assert "pinned_ok" in payload


def test_stop_blocks_then_caps(
    isolated: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _ = make_repo(isolated / "repo")
    payload = _payload(root, "Stop", last_assistant_message="all tests pass")
    monkeypatch.setattr(entry, "read_stdin", lambda: payload)

    for _ in range(2):
        assert entry.handle("Stop") == 0
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["decision"] == "block"

    # Third stop reaches MAX_BLOCKS and must fail open (never loop forever).
    assert entry.handle("Stop") == 0
    assert capsys.readouterr().out == ""
    decisions = [r["payload"] for r in _records(root) if r["event"] == "gate_decision"]
    assert isinstance(decisions[-1], dict)
    assert decisions[-1]["block"] is False
    assert decisions[-1]["capped"] is True


def test_stop_hook_active_does_not_block(
    isolated: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _ = make_repo(isolated / "repo")
    payload = _payload(
        root,
        "Stop",
        last_assistant_message="all tests pass",
        stop_hook_active=True,
    )
    monkeypatch.setattr(entry, "read_stdin", lambda: payload)
    assert entry.handle("Stop") == 0
    assert capsys.readouterr().out == ""
    decision = next(r["payload"] for r in _records(root) if r["event"] == "gate_decision")
    assert isinstance(decision, dict)
    assert decision["capped"] is True and decision["block"] is False


def test_stop_uses_test_message_override(isolated: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _ = make_repo(isolated / "repo")
    monkeypatch.setenv("AIPROOF_TEST_MESSAGE", "all tests pass")
    payload = _payload(root, "Stop", last_assistant_message="nothing to see")
    monkeypatch.setattr(entry, "read_stdin", lambda: payload)
    assert entry.handle("Stop") == 0
    claims = next(r for r in _records(root) if r["event"] == "claims_extracted")
    assert claims["payload"]["count"] >= 1


def test_unknown_event_is_noop(isolated: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _ = make_repo(isolated / "repo")
    monkeypatch.setattr(entry, "read_stdin", lambda: _payload(root, "Notification"))
    assert entry.handle("Notification") == 0
    assert _records(root) == []


# --------------------------------------------------------------------------- #
# fail-open + CLI
# --------------------------------------------------------------------------- #
def test_safe_handle_fails_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))

    def boom(_event: str) -> int:
        raise RuntimeError("boom")

    monkeypatch.setattr(entry, "handle", boom)
    assert entry._safe_handle("Stop") == 0
    log = paths.log_path()
    assert log.is_file()
    assert "internal error" in log.read_text(encoding="utf-8")


def test_main_usage_and_dispatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert entry.main([]) == 2
    assert "usage" in capsys.readouterr().err
    monkeypatch.setattr(entry, "_safe_handle", lambda event: 9)
    assert entry.main(["SessionStart"]) == 9
