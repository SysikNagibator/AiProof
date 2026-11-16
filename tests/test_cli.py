"""CLI: parsing, version, agents list, language, JSON output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiproof import version_string
from aiproof.cli import build_parser, main


def test_version_string_branding() -> None:
    assert version_string().startswith("AiProof ")
    assert version_string().endswith("by SYSIK")


def test_parser_has_expected_subcommands() -> None:
    parser = build_parser()
    actions = [a.dest for a in parser._actions if a.dest == "command"]
    assert actions
    choices = parser._subparsers._group_actions[0].choices  # type: ignore[attr-defined]
    for name in (
        "init",
        "doctor",
        "agents",
        "bench",
        "mcp",
        "hook",
        "tui",
        "verify",
        "learn",
        "checks",
        "watch",
        "setup",
        "install",
        "off",
        "keys",
        "receipt",
    ):
        assert name in choices


def test_version_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    assert "by SYSIK" in capsys.readouterr().out


def test_about_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["about"]) == 0
    out = capsys.readouterr().out
    assert "MIT" in out


def test_agents_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["agents"]) == 0
    out = capsys.readouterr().out
    assert "claude-code" in out
    assert "native-hooks" in out


def test_agents_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", "agents"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert any(a["id"] == "claude-code" for a in data)


def test_lang_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["lang"]) == 0
    assert "current:" in capsys.readouterr().out


def test_lang_flag_forces_language(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIPROOF_LANG", raising=False)
    assert main(["--lang", "ru", "about"]) == 0
    assert "Лицензия MIT" in capsys.readouterr().out


def test_verify_blocks(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(["verify", "all tests pass"])
    assert code == 1
    assert "tests_pass" in capsys.readouterr().out


def test_help_when_no_command_and_not_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert main([]) == 0


def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))


def test_checks_command(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["checks"]) == 0
    out = capsys.readouterr().out
    assert "strictness:" in out and "tests_ran" in out


def test_checks_change_refused_without_tty(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    monkeypatch.delenv("CI", raising=False)
    assert main(["checks", "strict"]) == 2
    assert "interactive human terminal" in capsys.readouterr().out


def test_install_list_ides(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["install", "--list-ides"]) == 0
    out = capsys.readouterr().out
    assert "claude-code" in out and "wrapper" in out


def test_learn_empty(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["learn"]) == 0
    assert "corrections: 0" in capsys.readouterr().out


def test_correct_then_learn(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["correct", "please be more careful"]) == 0
    assert "C001" in capsys.readouterr().out
    assert main(["learn"]) == 0
    assert "C001" in capsys.readouterr().out


def test_learn_compile(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["correct", "never run `git push --force`"]) == 0
    capsys.readouterr()
    assert main(["learn", "compile"]) == 0
    assert "compiled" in capsys.readouterr().out


def test_setup_dry_run(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["setup", "--dry-run"]) == 0
    assert "plan:" in capsys.readouterr().out


def test_watch_once(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["correct", "keep tests honest"]) == 0
    capsys.readouterr()
    assert main(["watch", "--once"]) == 0
    assert "correction" in capsys.readouterr().out


def test_keys_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["keys"]) == 0
    assert "->" in capsys.readouterr().out


def test_receipt_alias(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["receipt"]) == 1
    assert "no sessions" in capsys.readouterr().out
