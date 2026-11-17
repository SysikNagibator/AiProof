"""CLI: end-to-end coverage of every subcommand and its failure paths."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

from aiproof import paths
from aiproof.bench.harness import make_repo
from aiproof.cli import main
from aiproof.ledger.store import LedgerStore
from aiproof.maintenance.update import UpdateInfo

SECRET = "AKIA" + "IOSFODNN7EXAMPLE"


def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AIPROOF_LANG", "en")
    monkeypatch.delenv("AIPROOF_DISABLE", raising=False)


def _seed_session(root: Path) -> None:
    store = LedgerStore(root)
    store.append("session_start", {"start_commit": None}, session="s1")
    store.append(
        "gate_decision",
        {"block": False, "reason": "ok", "results": [], "findings": []},
        session="s1",
    )


# --------------------------------------------------------------------------- #
# status / sessions / receipts
# --------------------------------------------------------------------------- #
def test_status_text_and_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "AiProof by SYSIK" in out

    assert main(["status", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["project"] == str(paths.canonical_path(tmp_path))
    assert data["paused"] is False


def test_status_reports_pause(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    from aiproof.maintenance import pause

    monkeypatch.setattr(pause, "require_human", lambda _action: None)
    assert main(["pause", "5"]) == 0
    capsys.readouterr()
    assert main(["status"]) == 0
    assert "paused" in capsys.readouterr().out.lower()


def test_sessions_and_show_empty(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["sessions"]) == 0
    assert "no sessions" in capsys.readouterr().out.lower()
    assert main(["sessions", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert main(["show"]) == 1
    assert "no sessions" in capsys.readouterr().out.lower()


def test_show_formats(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_session(tmp_path)
    assert main(["sessions"]) == 0
    assert "s1" in capsys.readouterr().out
    for fmt in ("md", "json", "html"):
        assert main(["show", "s1", "--format", fmt]) == 0
        out = capsys.readouterr().out
        assert "s1" in out
    assert main(["report", "s1", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["session"] == "s1"


def test_ledger_verify(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_session(tmp_path)
    assert main(["ledger", "verify"]) == 0
    capsys.readouterr()
    assert main(["ledger", "verify", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


# --------------------------------------------------------------------------- #
# doctor / bench / scan / verify
# --------------------------------------------------------------------------- #
def test_doctor_text_and_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    main(["doctor"])
    capsys.readouterr()
    assert main(["doctor", "--json"]) in (0, 1)
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, list)


def test_bench_md_and_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["bench", "--md"]) == 0
    assert "AiProof benchmark" in capsys.readouterr().out
    assert main(["bench", "--json"]) == 0
    assert "detection_rate" in json.loads(capsys.readouterr().out)


def test_scan_empty_diff(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    root, _ = make_repo(tmp_path / "repo")
    monkeypatch.chdir(root)
    assert main(["scan"]) == 0
    assert "no secrets" in capsys.readouterr().out.lower()


def test_scan_untracked_secret_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    root, _ = make_repo(tmp_path / "repo")
    monkeypatch.chdir(root)
    (root / "leak.py").write_text(f'KEY = "{SECRET}"\n', encoding="utf-8")
    assert main(["scan", "--json"]) == 1
    findings = json.loads(capsys.readouterr().out)
    assert findings and findings[0]["path"] == "leak.py"
    assert main(["scan"]) == 1
    assert "leak.py" in capsys.readouterr().out


def test_scan_tree_instructions_histories(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    root, _ = make_repo(tmp_path / "repo", {"notes.md": f"token {SECRET}\n"})
    (root / "AGENTS.md").write_text(f"key {SECRET}\n", encoding="utf-8")
    history = tmp_path / "history.jsonl"
    history.write_text(f'{{"k": "{SECRET}"}}\n', encoding="utf-8")
    from aiproof.redact import scanner

    monkeypatch.setattr(scanner, "agent_history_paths", lambda: [history])
    monkeypatch.chdir(root)
    assert main(["scan", "--tree"]) == 1
    capsys.readouterr()
    assert main(["scan", "--instructions"]) == 1
    capsys.readouterr()
    assert main(["scan", "--histories"]) == 1
    capsys.readouterr()


def test_verify_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["verify", "all tests pass", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["block"] is True


# --------------------------------------------------------------------------- #
# pin / pause / resume / human-only commands
# --------------------------------------------------------------------------- #
def test_human_only_commands_refuse_without_tty(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    monkeypatch.setenv("AIPROOF_NON_INTERACTIVE", "1")
    monkeypatch.delenv("CI", raising=False)
    for argv in (["pin"], ["pause", "1"], ["resume"], ["off"]):
        assert main(argv) == 2
        assert "interactive human terminal" in capsys.readouterr().out


def test_pause_resume_roundtrip(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    from aiproof.maintenance import pause

    monkeypatch.setattr(pause, "require_human", lambda _action: None)
    assert main(["pause", "1"]) == 0
    assert "paused" in capsys.readouterr().out.lower()
    assert main(["resume"]) == 0
    assert "resumed" in capsys.readouterr().out.lower()
    assert not pause.is_paused(tmp_path)


def test_pin_succeeds_for_human(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    from aiproof.guard import pin

    monkeypatch.setattr(pin, "require_human", lambda _action: None)
    assert main(["init"]) == 0
    capsys.readouterr()
    assert main(["pin"]) == 0
    assert "pinned:" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# lang / theme / logs / update
# --------------------------------------------------------------------------- #
def test_lang_sets_and_rejects(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["lang", "ru"]) == 0
    assert "ru" in capsys.readouterr().out
    text = paths.global_config_path().read_text(encoding="utf-8")
    assert 'language = "ru"' in text
    assert main(["lang", "xx"]) == 2
    assert "unknown language" in capsys.readouterr().out


def test_lang_and_theme_survive_corrupt_global_config(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    target = paths.global_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("this is [not toml\n", encoding="utf-8")
    assert main(["theme", "mono"]) == 0
    capsys.readouterr()
    assert main(["lang", "en"]) == 0
    data = target.read_text(encoding="utf-8")
    assert 'theme = "mono"' in data and 'language = "en"' in data


def test_theme_list_and_set(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["theme"]) == 0
    assert "green" in capsys.readouterr().out
    assert main(["theme", "amber"]) == 0
    assert "amber" in capsys.readouterr().out


def test_logs_missing_and_invalid_utf8(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["logs"]) == 0
    assert "no logs" in capsys.readouterr().out.lower()
    log = paths.log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_bytes(b"hello\n\xff\xfe broken\nlast\n")
    assert main(["logs", "--lines", "2"]) == 0
    out = capsys.readouterr().out
    assert "broken" in out and "last" in out and "hello" not in out


def test_update_hint_and_check(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    from aiproof.maintenance import update

    assert main(["update"]) == 0
    assert "update" in capsys.readouterr().out.lower()

    monkeypatch.setattr(
        update, "check", lambda: UpdateInfo("1.0.0", "1.1.0", True, url="https://x")
    )
    assert main(["update", "--check"]) == 0
    assert "1.1.0" in capsys.readouterr().out
    assert main(["update", "--check", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["newer"] is True

    monkeypatch.setattr(
        update, "check", lambda: UpdateInfo("1.0.0", "1.0.0", False, error="offline")
    )
    assert main(["update", "--check"]) == 1
    assert "offline" in capsys.readouterr().out
    assert main(["update", "--check", "--json"]) == 1


# --------------------------------------------------------------------------- #
# corrections / learn
# --------------------------------------------------------------------------- #
def test_correct_json_and_duplicate(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["correct", "be careful", "--json"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["created"] is True
    assert main(["correct", "be careful", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["created"] is False


def test_learn_list_json_and_compile_write(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["learn", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"corrections": [], "rules": []}
    assert main(["correct", "never run `git push --force`"]) == 0
    capsys.readouterr()
    assert main(["learn", "compile"]) == 0
    assert "compiled" in capsys.readouterr().out
    assert main(["learn", "compile", "--write", "--json"]) == 0
    candidates = json.loads(capsys.readouterr().out)
    assert any(item.get("compiled") for item in candidates)
    assert main(["learn", "compile", "--write"]) == 0
    assert "nothing to compile" in capsys.readouterr().out.lower()
    assert main(["learn", "export"]) == 0
    assert "AGENTS.md" in capsys.readouterr().out


def test_learn_enable_disable_and_unknowns(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    from aiproof.guard import pin
    from aiproof.learn import load_rules

    monkeypatch.setattr(pin, "require_human", lambda _action: None)
    assert main(["correct", "never run `git push --force`"]) == 0
    capsys.readouterr()
    assert main(["learn", "compile", "--write"]) == 0
    capsys.readouterr()
    rule_id = load_rules(paths.rules_path(tmp_path))[0].id
    assert main(["learn", "disable", rule_id]) == 0
    assert main(["learn", "enable", rule_id]) == 0
    capsys.readouterr()
    assert main(["learn", "enable", "nope"]) == 1
    assert main(["learn", "enable"]) == 2
    assert main(["learn", "backtest", "nope"]) == 1
    assert main(["learn", "backtest"]) == 2


def test_learn_backtest(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    root, _ = make_repo(tmp_path / "repo")
    monkeypatch.chdir(root)
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))
    assert main(["correct", "never run `git push --force`"]) == 0
    capsys.readouterr()
    assert main(["learn", "compile", "--write"]) == 0
    capsys.readouterr()
    from aiproof.learn import load_rules

    rule_id = load_rules(paths.rules_path(root))[0].id
    assert main(["learn", "backtest", rule_id, "--json"]) == 0
    assert "would_have_caught" in json.loads(capsys.readouterr().out)


def test_learn_unknown_action(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    from aiproof.cli import cmd_learn

    assert cmd_learn(argparse.Namespace(action="bogus", json=False)) == 2
    assert "bogus" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# checks / watch / setup / install / off / keys
# --------------------------------------------------------------------------- #
def test_checks_json_and_write(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    from aiproof.guard import pin

    monkeypatch.setattr(pin, "require_human", lambda _action: None)
    assert main(["checks", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert any(item["name"] == "tests_ran" for item in payload["checks"])
    assert main(["checks", "strict"]) == 0
    capsys.readouterr()
    assert main(["checks", "--enable", "tests_ran", "--disable", "todo_integrity"]) == 0
    capsys.readouterr()
    assert main(["checks", "--enable", "nope"]) == 1
    assert "unknown check" in capsys.readouterr().out


def test_watch_once(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    _seed_session(tmp_path)
    assert main(["watch", "--once"]) == 0
    out = capsys.readouterr().out
    assert "gate_decision" in out
    assert main(["watch", "--once", "--json"]) == 0
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert lines and lines[-1]["session"] == "s1"


def test_setup_yes_runs_self_test(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["setup", "--yes"]) == 0
    assert "self-test" in capsys.readouterr().out.lower()


def test_install_paths(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["install"]) == 2
    assert main(["install", "--ide", "nope"]) == 1
    assert main(["install", "--ide", "claude-code", "--dry-run"]) == 0
    capsys.readouterr()
    assert main(["install", "--ide", "cursor", "--dry-run"]) == 0
    assert "cursor" in capsys.readouterr().out
    assert main(["install", "--ide", "aider"]) == 0
    assert "wrapper" in capsys.readouterr().out


def test_off_removes_hooks(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    from aiproof.guard import pin

    monkeypatch.setattr(pin, "require_human", lambda _action: None)
    assert main(["init"]) == 0
    capsys.readouterr()
    assert main(["off"]) == 0
    assert "hooks removed" in capsys.readouterr().out.lower()


def test_keys_text_and_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert main(["keys"]) == 0
    assert "quit" in capsys.readouterr().out
    assert main(["keys", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["q"] == "quit"


# --------------------------------------------------------------------------- #
# delegation and argument handling
# --------------------------------------------------------------------------- #
def test_run_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    from aiproof.adapters import wrapper

    seen: list[list[str]] = []
    monkeypatch.setattr(wrapper, "run_wrapped", lambda command, root: seen.append(command) or 7)
    assert main(["run", "--", "echo", "hi"]) == 7
    assert seen and "echo" in seen[0]


def test_hook_mcp_tui_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    from aiproof.hooks import entry
    from aiproof.mcp import server
    from aiproof.tui import app

    monkeypatch.setattr(entry, "main", lambda argv: 3)
    monkeypatch.setattr(server, "main", lambda: 4)
    monkeypatch.setattr(app, "run_tui", lambda **_: 5)
    assert main(["hook", "Stop"]) == 3
    assert main(["mcp"]) == 4
    assert main(["tui", "--ascii", "--no-anim"]) == 5


def test_main_tty_without_command_starts_tui(monkeypatch: pytest.MonkeyPatch) -> None:
    import aiproof.cli as cli

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli, "cmd_tui", lambda _args: 6)
    assert cli.main([]) == 6


def test_main_lang_equals_form(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIPROOF_LANG", raising=False)
    assert main(["--lang=ru", "about"]) == 0
    assert "Лицензия MIT" in capsys.readouterr().out
