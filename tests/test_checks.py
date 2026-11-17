"""Checks: test-run parsing, commit verification, file changes."""

from __future__ import annotations

from pathlib import Path

from aiproof.bench.harness import make_ctx, make_repo, manual, rec
from aiproof.checks import commit_exists, file_changed, tests_ran
from aiproof.claims.model import ClaimType


def test_parse_counts_pytest() -> None:
    counts = tests_ran.parse_counts("31 passed, 2 failed, 1 skipped in 0.4s")
    assert counts.passed == 31 and counts.failed == 2 and counts.skipped == 1


def test_parse_counts_jest() -> None:
    counts = tests_ran.parse_counts("Tests:       3 passed, 1 failed")
    assert counts.passed == 3 and counts.failed == 1


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
