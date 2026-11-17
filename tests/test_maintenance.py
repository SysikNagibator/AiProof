"""Maintenance: doctor, update and pause must never crash on bad local state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiproof import paths
from aiproof.adapters.claude_code import ClaudeCodeAdapter
from aiproof.maintenance import doctor, pause, update


@pytest.fixture(autouse=True)
def _isolated_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))


def test_doctor_reports_malformed_settings_without_raising(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"hooks": "aiproof hook"', encoding="utf-8")
    lines = doctor.run(tmp_path)
    assert any("not valid JSON" in line.label for line in lines)
    assert all(line.level in {doctor.OK, doctor.WARN, doctor.FAIL} for line in lines)


def test_doctor_detects_local_level_hooks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    ClaudeCodeAdapter().install(tmp_path, level="local")
    state, path = ClaudeCodeAdapter().hook_status(tmp_path)
    assert state == "installed"
    assert path == tmp_path / ".claude" / "settings.local.json"
    assert any("installed" in line.label for line in doctor.run(tmp_path))


def test_update_reports_network_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("offline")

    monkeypatch.setattr(update.urllib.request, "urlopen", boom)
    info = update.check()
    assert not info.ok
    assert "offline" in info.error


def test_update_rejects_non_object_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self) -> bytes:
            return b"[1, 2, 3]"

    monkeypatch.setattr(update.urllib.request, "urlopen", lambda *_a, **_k: Response())
    info = update.check()
    assert not info.ok
    assert "invalid JSON" in info.error


def test_pause_ignores_non_utf8_state(tmp_path: Path) -> None:
    state = paths.project_dir(tmp_path) / "state.json"
    state.parent.mkdir(parents=True)
    state.write_bytes(b"\xff\xfe{not json")
    assert pause.is_paused(tmp_path) is False


def test_pause_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pause, "require_human", lambda _action: None)
    pause.pause(tmp_path, 5)
    assert pause.is_paused(tmp_path)
    pause.resume(tmp_path)
    assert not pause.is_paused(tmp_path)
    state = paths.project_dir(tmp_path) / "state.json"
    assert isinstance(json.loads(state.read_text(encoding="utf-8")), dict)
