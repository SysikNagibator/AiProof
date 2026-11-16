"""Config: layered settings, pins and integrity."""

from __future__ import annotations

import os
from pathlib import Path

from aiproof.config import (
    Settings,
    load_settings,
    merge_pinned,
    pin_digest,
    pinned_ok,
    read_pinned,
    write_pinned,
)


def test_pin_roundtrip(tmp_path: Path) -> None:
    settings = Settings(strictness="strict", test_command="pytest -q")
    pinned = write_pinned(tmp_path, settings)
    read = read_pinned(tmp_path)
    assert read is not None
    assert read.sha256 == pinned.sha256
    assert pinned_ok(tmp_path)[0]


def test_pin_tamper_detected(tmp_path: Path) -> None:
    write_pinned(tmp_path, Settings(strictness="enforce"))
    from aiproof import paths

    pinned_file = paths.pinned_path(tmp_path)
    # Tampering a critical value must be detected (comment-only edits are ignored).
    pinned_file.write_text(
        pinned_file.read_text(encoding="utf-8").replace('"enforce"', '"observe"'),
        encoding="utf-8",
    )
    ok, reason = pinned_ok(tmp_path)
    assert not ok and "tamper" in reason


def test_env_override(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setenv("AIPROOF_STRICTNESS", "observe")  # type: ignore[attr-defined]
    assert load_settings(tmp_path).strictness == "observe"


def test_merge_pinned_wins(tmp_path: Path) -> None:
    write_pinned(tmp_path, Settings(strictness="strict"))
    merged = merge_pinned(Settings(strictness="observe"), read_pinned(tmp_path))
    assert merged.strictness == "strict"


def test_pin_digest_stable() -> None:
    a = Settings(strictness="enforce")
    b = Settings(strictness="enforce", language="ru")
    assert pin_digest(a) == pin_digest(b)  # language is not gate-critical


def test_os_module_unused_guard() -> None:
    assert os is not None
