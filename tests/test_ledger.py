"""Ledger: append, chain verify, tamper detection."""

from __future__ import annotations

from pathlib import Path

from aiproof import paths
from aiproof.ledger import verify
from aiproof.ledger.store import LedgerStore


def test_append_and_verify(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path)
    store.append("session_start", {"a": 1}, session="s1")
    store.append("gate_decision", {"block": False}, session="s1")
    result = verify.verify(tmp_path)
    assert result.ok
    assert result.checked == 2
    assert store.last_session() == "s1"


def test_tamper_detected(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path)
    store.append("gate_decision", {"block": False}, session="s1")
    ledger = paths.ledger_path(tmp_path)
    ledger.write_text(ledger.read_text().replace("false", "true"), encoding="utf-8")
    assert not verify.verify(tmp_path).ok


def test_secret_never_written(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path)
    store.append("secret_found", {"detail": "AKIAIOSFODNN7EXAMPLE"}, session="s1")
    text = paths.ledger_path(tmp_path).read_text(encoding="utf-8")
    assert "AKIAIOSFODNN7EXAMPLE" not in text
    assert "REDACTED" in text


def test_rotation_keeps_chain(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path, rotate_bytes=200)
    for i in range(50):
        store.append("tool_post", {"command": f"cmd {i}", "output": "x" * 20}, session="s1")
    result = verify.verify(tmp_path)
    assert result.ok
    assert result.segments >= 2
