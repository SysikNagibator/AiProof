"""Wrapper mode: post-hoc verification and honest exit codes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from aiproof.adapters.wrapper import run_wrapped


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AIPROOF_NON_INTERACTIVE", "1")
    monkeypatch.setenv("AIPROOF_LANG", "en")
    root = tmp_path / "repo"
    root.mkdir()
    return root


def _cmd(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_wrapper_returns_zero_for_honest_output(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_wrapped(_cmd("print('hello there')"), repo) == 0
    assert "AiProof (wrapper, post-hoc)" in capsys.readouterr().out


def test_wrapper_returns_one_on_false_file_claim(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = run_wrapped(_cmd("print('Created the file src/missing.py.')"), repo)
    assert rc == 1
    assert "FAIL" in capsys.readouterr().out


def test_wrapper_preserves_agent_nonzero_exit(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = run_wrapped(_cmd("import sys; sys.exit(3)"), repo)
    assert rc == 3
    capsys.readouterr()
