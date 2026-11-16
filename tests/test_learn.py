"""Phase 2: corrections, rule DSL, compile, backtest and AGENTS.md export."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aiproof import paths
from aiproof.learn.backtest import backtest, collect_history
from aiproof.learn.compile import compile_all, compile_correction
from aiproof.learn.corrections import (
    list_corrections,
    record_correction,
)
from aiproof.learn.dsl import (
    DiffFile,
    Rule,
    RuleError,
    apply_rule,
    apply_rules,
    load_rules,
    matches_scope,
    save_rules,
    set_enabled,
    upsert_rule,
    validate_rule,
)
from aiproof.learn.export import MARKER_END, MARKER_START, render_block, upsert_block, write_export


@pytest.fixture(autouse=True)
def _isolated_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIPROOF_DATA_DIR", str(tmp_path / "data"))


def test_record_and_dedupe(tmp_path: Path) -> None:
    first, created = record_correction(tmp_path, "Do not mock the database in integration tests")
    assert created
    assert first.id == "C001"
    again, created_again = record_correction(
        tmp_path, "  do not   MOCK the database in integration tests "
    )
    assert not created_again
    assert again.id == first.id
    assert len(list_corrections(tmp_path)) == 1


def test_correction_is_redacted(tmp_path: Path) -> None:
    record_correction(tmp_path, "never commit AKIAIOSFODNN7EXAMPLE anywhere")
    ledger = paths.ledger_path(tmp_path).read_text(encoding="utf-8")
    assert "AKIAIOSFODNN7EXAMPLE" not in ledger
    assert "REDACTED" in ledger


def test_compile_db_mock(tmp_path: Path) -> None:
    correction, _ = record_correction(tmp_path, "Do not mock the database in integration tests")
    candidate = compile_correction(correction)
    assert candidate.compiled
    assert candidate.rule is not None
    assert candidate.rule.id == "no-db-mock-in-integration"
    assert candidate.rule.scope == "tests/integration/**/*.py"
    assert not candidate.rule.enabled


def test_compile_command_import_and_path(tmp_path: Path) -> None:
    command, _ = record_correction(tmp_path, "never run `git push --force`")
    imported, _ = record_correction(tmp_path, "never import django in src/**/*.py")
    locked, _ = record_correction(tmp_path, "never edit .github/workflows/ci.yml")
    assert compile_correction(command).rule is not None
    assert compile_correction(imported).rule is not None
    assert compile_correction(locked).rule is not None


def test_vague_correction_stays_advisory(tmp_path: Path) -> None:
    correction, _ = record_correction(tmp_path, "please be more careful next time")
    candidate = compile_correction(correction)
    assert not candidate.compiled
    assert candidate.rule is None
    assert "advisory" in candidate.reason


def test_compile_all_skips_linked(tmp_path: Path) -> None:
    correction, _ = record_correction(tmp_path, "Do not mock the database in integration tests")
    linked = Rule(
        id="no-db-mock-in-integration",
        description="linked",
        source_correction=correction.id,
    )
    assert compile_all(tmp_path, [linked]) == []
    assert len(compile_all(tmp_path)) == 1


def test_glob_scope() -> None:
    assert matches_scope("tests/integration/**/*.py", "tests/integration/a/b.py")
    assert matches_scope("tests/integration/**/*.py", "tests/integration/x.py")
    assert not matches_scope("tests/integration/**/*.py", "src/app.py")


def test_rule_roundtrip(tmp_path: Path) -> None:
    rule = Rule(
        id="r1",
        description="no print",
        scope="src/**/*.py",
        forbid_added_regex=(r"\bprint\(",),
        severity="block",
        enabled=True,
    )
    path = tmp_path / "rules.toml"
    save_rules(path, [rule])
    loaded = load_rules(path)
    assert len(loaded) == 1
    assert loaded[0].to_dict() == rule.to_dict()


def test_invalid_rule_rejected() -> None:
    with pytest.raises(RuleError):
        validate_rule(Rule(id="bad", description="x", severity="nuclear"))
    with pytest.raises(RuleError):
        validate_rule(Rule(id="bad", description="x", forbid_added_regex=("[",)))


def test_apply_rule_and_waiver() -> None:
    rule = Rule(
        id="r1",
        description="no secret print",
        scope="src/**/*.py",
        forbid_added_regex=(r"print\(",),
        severity="block",
        enabled=True,
    )
    files = [DiffFile("src/a.py", ("print(1)", "x = 1"))]
    hits = apply_rule(rule, files)
    assert len(hits) == 1 and hits[0].line == 1
    waived = [DiffFile("src/a.py", ("print(1)  # aiproof:ignore",))]
    assert apply_rule(rule, waived) == []
    assert len(apply_rule(rule, waived, include_waivers=True)) == 1


def test_require_pattern_missing() -> None:
    rule = Rule(
        id="needs-test",
        description="integration changes need a test",
        scope="src/**/*.py",
        require_added_regex=(r"def test_",),
        enabled=True,
    )
    hits = apply_rule(rule, [DiffFile("src/a.py", ("x = 1",))])
    assert hits and hits[0].line == 0
    assert apply_rule(rule, [DiffFile("src/a.py", ("def test_x():",))]) == []


def test_apply_rules_only_enabled() -> None:
    enabled = Rule(id="on", description="x", forbid_command_regex=("rm",), enabled=True)
    disabled = Rule(id="off", description="x", forbid_command_regex=("rm",), enabled=False)
    hits = apply_rules([enabled, disabled], [], ["rm -rf build"])
    assert [hit.rule_id for hit in hits] == ["on"]


def test_set_and_upsert() -> None:
    rules = [Rule(id="a", description="a")]
    rules = upsert_rule(rules, Rule(id="a", description="updated"))
    assert rules[0].description == "updated"
    rules = set_enabled(rules, "a", True)
    assert rules[0].enabled
    with pytest.raises(KeyError):
        set_enabled(rules, "missing", True)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def test_backtest_finds_historical_hit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "tests" / "integration").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    target = repo / "tests" / "integration" / "test_db.py"
    target.write_text("mock.patch('db')\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    assert len(collect_history(repo)) == 1
    rule = Rule(
        id="no-db-mock-in-integration",
        description="no db mock",
        scope="tests/integration/**/*.py",
        forbid_added_regex=(r"mock\.patch\(.*db",),
        severity="block",
    )
    result = backtest(repo, rule)
    assert result.commits_scanned == 1
    assert result.would_have_caught == 1
    assert result.samples


def test_export_preserves_user_text_and_is_idempotent(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text("# My rules\n\nKeep this line.\n", encoding="utf-8")
    rules = [
        Rule(id="r1", description="no print", enabled=True, severity="block"),
        Rule(id="r2", description="disabled rule", enabled=False),
    ]
    path, changed = write_export(tmp_path, rules, target="AGENTS.md")
    text = path.read_text(encoding="utf-8")
    assert changed
    assert "Keep this line." in text
    assert MARKER_START in text and MARKER_END in text
    assert "r1" in text and "r2" not in text
    _path, changed_again = write_export(tmp_path, rules, target="AGENTS.md")
    assert not changed_again


def test_upsert_block_replaces_old_block() -> None:
    old = f"before\n{MARKER_START}\nold\n{MARKER_END}\nafter\n"
    new = upsert_block(old, f"{MARKER_START}\nnew\n{MARKER_END}")
    assert "before" in new and "after" in new
    assert "old" not in new and "new" in new


def test_render_block_empty() -> None:
    block = render_block([], "en")
    assert "No rules are enabled" in block


def test_enabled_rule_blocks_the_gate(tmp_path: Path) -> None:
    from aiproof.checks.base import CheckContext
    from aiproof.checks.learn_rules import run as run_learn
    from aiproof.config import Settings
    from aiproof.gate.gate import decide

    rule = Rule(
        id="no-force-push",
        description="never force-push",
        forbid_command_regex=(r"git push --force",),
        severity="block",
        enabled=True,
    )
    save_rules(paths.rules_path(tmp_path), [rule])
    ctx = CheckContext(
        root=tmp_path,
        settings=Settings(),
        session="t",
        records=[{"event": "tool_post", "payload": {"command": "git push --force"}}],
    )
    findings = run_learn(ctx)
    assert findings and findings[0].verdict.value == "fail"
    assert decide(ctx).block


def test_disabled_rule_does_not_block(tmp_path: Path) -> None:
    from aiproof.checks.base import CheckContext
    from aiproof.checks.learn_rules import run as run_learn
    from aiproof.config import Settings

    rule = Rule(
        id="no-force-push",
        description="never force-push",
        forbid_command_regex=(r"git push --force",),
        severity="block",
        enabled=False,
    )
    save_rules(paths.rules_path(tmp_path), [rule])
    ctx = CheckContext(
        root=tmp_path,
        settings=Settings(),
        session="t",
        records=[{"event": "tool_post", "payload": {"command": "git push --force"}}],
    )
    assert run_learn(ctx) == []
