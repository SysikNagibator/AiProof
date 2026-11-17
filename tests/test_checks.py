"""Checks: test-run parsing, commit verification, file changes."""

from __future__ import annotations

from pathlib import Path

from aiproof.bench.harness import make_ctx, make_repo, manual, rec
from aiproof.checks import commit_exists, file_changed, test_tamper, tests_ran
from aiproof.claims.model import ClaimType


def test_parse_counts_pytest() -> None:
    counts = tests_ran.parse_counts("31 passed, 2 failed, 1 skipped in 0.4s")
    assert counts.passed == 31 and counts.failed == 2 and counts.skipped == 1


def test_parse_counts_jest() -> None:
    counts = tests_ran.parse_counts("Tests:       3 passed, 1 failed")
    assert counts.passed == 3 and counts.failed == 1


def test_no_tests_regex_ignores_numeric_prefix() -> None:
    """Regression: ``20 tests`` must not match the ``0 tests`` no-tests phrase."""
    assert not tests_ran.NO_TESTS_RE.search("Ran 20 tests in 0.1s")
    assert not tests_ran.NO_TESTS_RE.search("10 tests passed")
    assert tests_ran.NO_TESTS_RE.search("collected 0 items")
    assert tests_ran.NO_TESTS_RE.search("0 tests")


def test_parse_counts_unittest_ok() -> None:
    counts = tests_ran.parse_counts("Ran 20 tests in 0.123s\n\nOK")
    assert counts.saw_any and counts.passed == 20 and counts.failed == 0


def test_parse_counts_unittest_failed() -> None:
    counts = tests_ran.parse_counts("Ran 3 tests in 0.1s\n\nFAILED (failures=1, errors=2)")
    assert counts.saw_any and counts.failed == 3 and counts.passed == 0


def test_tests_ran_strict_unittest_honest_pass(tmp_path: Path) -> None:
    """Regression: an honest unittest run must not be blocked in strict mode."""
    root, head = make_repo(tmp_path)
    ctx = make_ctx(
        root,
        claims_text="all tests pass",
        strictness="strict",
        start_commit=head,
        records=[
            rec(
                "tool_post",
                {"command": "python -m unittest", "output": "Ran 20 tests in 0.1s\n\nOK"},
            )
        ],
    )
    result = tests_ran.check(ctx.claims[0], ctx)
    assert result.verdict.value == "pass"


def test_commit_exists_fake(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path)
    claim = manual(ClaimType.COMMITTED, "I committed")
    ctx = make_ctx(root, claims=[claim], start_commit=head)
    assert commit_exists.check(claim, ctx).verdict == "fail"


def test_commit_exists_real(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path)
    make_repo(root)  # keep dir
    (root / "src" / "app.py").write_text("def add(a, b):\n    return a + b + 1\n", encoding="utf-8")
    from aiproof.bench.harness import git

    git(root, "commit", "-qam", "change")
    claim = manual(ClaimType.COMMITTED, "committed")
    ctx = make_ctx(root, claims=[claim], start_commit=head)
    assert commit_exists.check(claim, ctx).verdict == "pass"


def test_file_changed_detects_no_change(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path, {"config.py": "V = 1\n"})
    claim = manual(ClaimType.FILE_WRITTEN, "created config.py", {"files": ["config.py"]})
    ctx = make_ctx(root, claims=[claim], start_commit=head)
    assert file_changed.check(claim, ctx).verdict == "fail"


def test_file_changed_real_change(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path, {"config.py": "V = 1\n"})
    (root / "config.py").write_text("V = 2\n", encoding="utf-8")
    claim = manual(ClaimType.FILE_CHANGED, "updated config.py", {"files": ["config.py"]})
    ctx = make_ctx(root, claims=[claim], start_commit=head)
    assert file_changed.check(claim, ctx).verdict == "pass"


def test_file_changed_snapshot_blocks_dirty_but_unchanged(tmp_path: Path) -> None:
    """A file already dirty at session start must not pass if left untouched.

    Without the session snapshot the ``start_commit`` fallback would see the file
    differs from HEAD and wrongly pass the claim.
    """
    from aiproof import gitutil

    root, head = make_repo(tmp_path, {"config.py": "V = 1\n"})
    (root / "dirty.py").write_text("DIRTY = 1\n", encoding="utf-8")
    snapshot = gitutil.snapshot_files(root)
    assert "dirty.py" in snapshot
    claim = manual(ClaimType.FILE_CHANGED, "updated dirty.py", {"files": ["dirty.py"]})
    ctx = make_ctx(
        root,
        claims=[claim],
        start_commit=head,
        records=[rec("file_snapshot", {"files": snapshot})],
    )
    assert file_changed.check(claim, ctx).verdict == "fail"


def test_file_changed_snapshot_passes_real_change(tmp_path: Path) -> None:
    from aiproof import gitutil

    root, head = make_repo(tmp_path, {"config.py": "V = 1\n"})
    (root / "dirty.py").write_text("DIRTY = 1\n", encoding="utf-8")
    snapshot = gitutil.snapshot_files(root)
    (root / "dirty.py").write_text("DIRTY = 2\n", encoding="utf-8")
    claim = manual(ClaimType.FILE_CHANGED, "updated dirty.py", {"files": ["dirty.py"]})
    ctx = make_ctx(
        root,
        claims=[claim],
        start_commit=head,
        records=[rec("file_snapshot", {"files": snapshot})],
    )
    assert file_changed.check(claim, ctx).verdict == "pass"


def test_file_deleted_claim_rejects_modified_file(tmp_path: Path) -> None:
    """A "deleted X" claim must not pass just because X changed."""
    root, head = make_repo(tmp_path, {"gone.py": "V = 1\n"})
    (root / "gone.py").write_text("V = 2\n", encoding="utf-8")
    claim = manual(ClaimType.FILE_DELETED, "deleted gone.py", {"files": ["gone.py"]})
    ctx = make_ctx(root, claims=[claim], start_commit=head)
    assert file_changed.check(claim, ctx).verdict == "fail"


def test_file_deleted_claim_passes_when_absent(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path, {"gone.py": "V = 1\n"})
    (root / "gone.py").unlink()
    claim = manual(ClaimType.FILE_DELETED, "deleted gone.py", {"files": ["gone.py"]})
    ctx = make_ctx(root, claims=[claim], start_commit=head)
    assert file_changed.check(claim, ctx).verdict == "pass"


def test_file_written_claim_rejects_deleted_file(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path, {"gone.py": "V = 1\n"})
    (root / "gone.py").unlink()
    claim = manual(ClaimType.FILE_WRITTEN, "wrote gone.py", {"files": ["gone.py"]})
    ctx = make_ctx(root, claims=[claim], start_commit=head)
    assert file_changed.check(claim, ctx).verdict == "fail"


def test_latest_run_is_authoritative(tmp_path: Path) -> None:
    """A later failing run must not be shadowed by an earlier, larger passing run."""
    from aiproof.bench.harness import tool_post

    root, head = make_repo(tmp_path)
    ctx = make_ctx(
        root,
        claims=[manual(ClaimType.TESTS_PASS, "12 passed", {"count": 12})],
        start_commit=head,
        records=[
            tool_post("pytest -q", "12 passed"),
            tool_post("pytest -q", "10 passed, 1 failed"),
        ],
    )
    result = tests_ran.check(ctx.claims[0], ctx)
    assert result.verdict.value == "fail"


def test_zero_tests_fails_in_default_enforce(tmp_path: Path) -> None:
    from aiproof.bench.harness import tool_post

    root, head = make_repo(tmp_path)
    ctx = make_ctx(
        root,
        claims_text="all tests pass",
        strictness="enforce",
        start_commit=head,
        records=[tool_post("pytest -q", "collected 0 items")],
    )
    assert tests_ran.check(ctx.claims[0], ctx).verdict.value == "fail"


def test_dotnet_parse_is_linear() -> None:
    import time

    start = time.perf_counter()
    tests_ran.parse_counts("Passed! " * 8000)
    assert time.perf_counter() - start < 2.0


# --------------------------------------------------------------------------- #
# test_tamper: justification must require a real source removal
# --------------------------------------------------------------------------- #
def _tamper_ctx(root: Path, head: str | None):
    return make_ctx(root, claims_text="all tests pass", start_commit=head)


def test_test_tamper_blocks_deleted_test_without_source_removal(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path, {"tests/test_auth.py": "def test_auth():\n    assert True\n"})
    (root / "tests" / "test_auth.py").unlink()
    assert test_tamper.run(_tamper_ctx(root, head))


def test_test_tamper_blocks_readme_touch_bypass(tmp_path: Path) -> None:
    """Touching an unrelated source file must not excuse deleting tests."""
    root, head = make_repo(
        tmp_path,
        {"tests/test_auth.py": "def test_auth():\n    assert True\n", "README.md": "hi\n"},
    )
    (root / "tests" / "test_auth.py").unlink()
    (root / "README.md").write_text("hi, changed\n", encoding="utf-8")
    findings = test_tamper.run(_tamper_ctx(root, head))
    assert any(f.verdict == "fail" for f in findings)


def test_test_tamper_blocks_modified_source_bypass(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path, {"tests/test_auth.py": "def test_auth():\n    assert True\n"})
    (root / "src" / "app.py").write_text("def add(a, b):\n    return a + b + 1\n", encoding="utf-8")
    (root / "tests" / "test_auth.py").unlink()
    assert test_tamper.run(_tamper_ctx(root, head))


def test_test_tamper_allows_test_removal_with_source_removal(tmp_path: Path) -> None:
    root, head = make_repo(
        tmp_path,
        {"tests/test_auth.py": "def test_auth():\n    assert True\n", "src/old.py": "X = 1\n"},
    )
    (root / "tests" / "test_auth.py").unlink()
    (root / "src" / "old.py").unlink()
    assert test_tamper.run(_tamper_ctx(root, head)) == []


def test_test_tamper_blocks_weakened_assertion_even_with_source_removal(tmp_path: Path) -> None:
    root, head = make_repo(
        tmp_path,
        {
            "tests/test_x.js": "expect(a).toBe(42)\n",
            "src/old.py": "X = 1\n",
        },
    )
    (root / "tests" / "test_x.js").write_text("expect(a).toBeTruthy()\n", encoding="utf-8")
    (root / "src" / "old.py").unlink()
    findings = test_tamper.run(_tamper_ctx(root, head))
    assert any("weakened" in f.reason for f in findings)
