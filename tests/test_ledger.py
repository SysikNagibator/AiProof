"""Ledger: append, chain verify, tamper detection."""

from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

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


def test_malformed_line_is_broken_chain_not_crash(tmp_path: Path) -> None:
    """A corrupt line must be reported as a broken chain, never crash."""
    store = LedgerStore(tmp_path)
    store.append("session_start", {"a": 1}, session="s1")
    store.append("gate_decision", {"block": False}, session="s1")
    ledger = paths.ledger_path(tmp_path)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write("{not valid json\n")
    result = verify.verify(tmp_path)
    assert not result.ok
    assert "malformed" in result.reason


def test_records_and_last_session_survive_malformed_line(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path)
    store.append("session_start", {"a": 1}, session="s1")
    ledger = paths.ledger_path(tmp_path)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write("garbage\n")
    assert store.records()  # best-effort: returns what it could read
    assert store.last_session() == "s1"


def test_append_after_corrupt_tail_does_not_crash(tmp_path: Path) -> None:
    """A corrupt tail must not make appending raise."""
    store = LedgerStore(tmp_path)
    store.append("session_start", {"a": 1}, session="s1")
    ledger = paths.ledger_path(tmp_path)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write("broken tail\n")
    store.append("gate_decision", {"block": False}, session="s1")
    assert not verify.verify(tmp_path).ok


def test_lock_timeout_raises_instead_of_entering_unlocked(tmp_path: Path) -> None:
    """Regression: a timeout used to proceed without the lock and fork the chain."""
    from aiproof.ledger._lock import file_lock

    path = tmp_path / ".lock"
    with file_lock(path), pytest.raises(TimeoutError), file_lock(path, timeout=0.05):
        raise AssertionError("must not enter the critical section")


def test_append_fails_loudly_when_lock_times_out(tmp_path: Path) -> None:
    import aiproof.ledger.store as store_module

    store = LedgerStore(tmp_path)
    store.append("session_start", {"a": 1}, session="s1")
    original = store_module.file_lock

    @contextlib.contextmanager
    def fake_lock(path: Path, timeout: float = 5.0):
        raise TimeoutError("busy")

    store_module.file_lock = fake_lock  # type: ignore[assignment]
    try:
        with pytest.raises(TimeoutError):
            store.append("gate_decision", {"block": False}, session="s1")
    finally:
        store_module.file_lock = original  # type: ignore[assignment]
    assert len(store.records()) == 1
