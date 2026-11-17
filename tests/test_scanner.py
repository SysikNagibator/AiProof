"""Scanner: diffs, trees, instruction files, histories and in-place redaction."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from aiproof.bench.harness import make_repo
from aiproof.redact import scanner
from aiproof.redact.redactor import Allowlist, find_secrets

SECRET = "ghp_" + "a" * 36


def test_scan_text_line_numbers_and_allowlist() -> None:
    text = f"first line\nkey = {SECRET}\nlast line\n"
    findings = scanner.scan_text(text, "x.py")
    assert len(findings) == 1
    assert findings[0].line == 2
    assert findings[0].path == "x.py"
    assert "ghp_" not in json.dumps(findings[0].as_dict())

    allowed = Allowlist(paths=("x.py",))
    assert scanner.scan_text(text, "x.py", allowed) == []
    assert scanner.scan_text(text, "nested/x.py", allowed)


def test_scan_file_relative_and_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    inside = root / "sub" / "a.py"
    inside.parent.mkdir()
    inside.write_text(SECRET, encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text(SECRET, encoding="utf-8")

    rel = scanner.scan_file(inside, root)
    assert rel and rel[0].path == "sub/a.py"
    absolute = scanner.scan_file(outside, root)
    assert absolute and absolute[0].path.endswith("outside.py")


def test_scan_file_missing_or_directory(tmp_path: Path) -> None:
    assert scanner.scan_file(tmp_path / "missing.txt") == []
    assert scanner.scan_file(tmp_path) == []


def test_scan_diff_covers_unstaged_staged_and_untracked(tmp_path: Path) -> None:
    root, _ = make_repo(tmp_path / "repo")
    (root / "src" / "app.py").write_text(f'KEY = "{SECRET}"\n', encoding="utf-8")
    staged = root / "staged.py"
    staged.write_text(f'TOKEN = "{SECRET}"\n', encoding="utf-8")
    subprocess_git(root, "add", "staged.py")
    (root / "untracked.py").write_text(f'OTHER = "{SECRET}"\n', encoding="utf-8")

    findings = scanner.scan_diff(root)
    paths = {finding.path for finding in findings}
    assert "<git-diff>" in paths
    assert "untracked.py" in paths


def subprocess_git(root: Path, *args: str) -> None:
    from aiproof.bench.harness import git

    git(root, *args)


def test_scan_tree_and_iter_tracked(tmp_path: Path) -> None:
    root, _ = make_repo(tmp_path / "repo", {"src/leak.py": SECRET})
    (root / "new.py").write_text(SECRET, encoding="utf-8")
    tracked = {path.name for path in scanner.iter_tracked(root)}
    assert {"leak.py", "new.py", "app.py"} <= tracked
    findings = scanner.scan_tree(root)
    assert {finding.path for finding in findings} >= {"src/leak.py", "new.py"}


def test_scan_instruction_files_file_and_directory(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "AGENTS.md").write_text(SECRET, encoding="utf-8")
    rules = root / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "one.md").write_text(SECRET, encoding="utf-8")
    findings = scanner.scan_instruction_files(root)
    assert {finding.path for finding in findings} == {"AGENTS.md", ".cursor/rules/one.md"}


def test_agent_history_paths_and_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    history = home / ".claude" / "history.jsonl"
    history.write_text(SECRET + "\n", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: home)
    assert history in scanner.agent_history_paths()
    findings = scanner.scan_agent_histories()
    assert findings and findings[0].path.endswith("history.jsonl")

    monkeypatch.setattr(scanner, "agent_history_paths", lambda: [history])
    assert scanner.scan_agent_histories()


def test_redact_in_place(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text(f"token {SECRET}\n", encoding="utf-8")
    changed, backup = scanner.redact_in_place(target)
    assert changed is True
    assert backup == os.fspath(target) + ".bak"
    assert SECRET not in target.read_text(encoding="utf-8")
    assert SECRET in Path(backup).read_text(encoding="utf-8")

    changed, backup = scanner.redact_in_place(target)
    assert changed is False and backup == ""

    missing = tmp_path / "missing.txt"
    changed, reason = scanner.redact_in_place(missing)
    assert changed is False and "cannot read" in reason


def test_redact_in_place_invalid_utf8_does_not_crash(tmp_path: Path) -> None:
    target = tmp_path / "binary.txt"
    target.write_bytes(b"\xff\xfe" + SECRET.encode())
    changed, reason = scanner.redact_in_place(target)
    assert changed is False and "cannot read" in reason


def test_find_secrets_used_by_scanner() -> None:
    assert find_secrets(SECRET)
    assert scanner.ScanFinding("p", "t", "abcdef12").as_dict()["path"] == "p"
