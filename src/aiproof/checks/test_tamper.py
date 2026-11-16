"""Integrity check: test tampering (deleted/weakened/skipped tests)."""

from __future__ import annotations

import re

from aiproof import gitutil
from aiproof.checks.base import CheckContext, IntegrityFinding
from aiproof.claims.model import Evidence, Verdict

NAME = "test_tamper"

TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|__tests__|spec)/|(^|/)(test_|conftest)|(_test|\.test|\.spec|Test|Tests|Spec)\.",
    re.IGNORECASE,
)
TEST_DEF_RE = re.compile(
    r"\b(def test_\w+|it\(|test\(|describe\(|func Test\w+|@Test|#\[(?:test|tokio::test)\])"
)
SKIP_ADDED_RE = re.compile(
    r"(pytest\.mark\.(?:skip|xfail)|@unittest\.skip|\b(?:it|test|describe)\.(?:only|skip)\b|"
    r"\.skip\(|\.todo\(|t\.Skip\(|#\[ignore\]|@Disabled|@Ignore)"
)
EXACT_MATCHER_RE = re.compile(r"(toBe|toEqual|assertEquals|assertEqual)\(\s*([^)]+)\)")
LOOSE_MATCHER_RE = re.compile(
    r"(toBeTruthy|toBeDefined|toBeGreaterThan|toBeLessThan|toContain|toBeInstanceOf|"
    r"assertIsNotNone|assertTrue|assertIsNotNone)\(\)"
)


def applies_here() -> bool:
    """Marker: this module is an integrity check."""
    return True


def _is_test_path(path: str) -> bool:
    return bool(TEST_PATH_RE.search(path))


def _diff(ctx: CheckContext) -> tuple[list[str], list[str], list[str]]:
    if ctx.start_commit is None:
        return [], [], []
    rc, out, _ = gitutil.run_git(ctx.root, ["diff", "--name-status", ctx.start_commit])
    deleted: list[str] = []
    changed: list[str] = []
    if rc != 0:
        return [], [], []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        changed.append(path)
        if status.startswith("D") and _is_test_path(path):
            deleted.append(path)
    return deleted, changed, out.splitlines()


def run(ctx: CheckContext) -> list[IntegrityFinding]:
    """Detect deleted tests, new skips, weakened assertions and lost test cases."""
    if ctx.start_commit is None:
        return []
    deleted, changed_files, _ = _diff(ctx)
    added = gitutil.added_lines_since(ctx.root, ctx.start_commit)
    removed = gitutil.removed_lines_since(ctx.root, ctx.start_commit)
    non_test_changed = [f for f in changed_files if not _is_test_path(f)]
    justified = bool(non_test_changed)

    findings: list[IntegrityFinding] = []
    evidence: list[Evidence] = []

    if deleted and not justified:
        evidence.append(
            Evidence("git", f"deleted test file(s): {', '.join(deleted)}", {"files": deleted})
        )
        findings.append(
            IntegrityFinding(
                NAME,
                Verdict.FAIL,
                f"test file(s) deleted without matching source removal: {', '.join(deleted)}",
                evidence,
            )
        )

    removed_defs = [ln for ln in removed if TEST_DEF_RE.search(ln)]
    added_defs = [ln for ln in added if TEST_DEF_RE.search(ln)]
    if removed_defs and len(removed_defs) > len(added_defs) and not justified:
        findings.append(
            IntegrityFinding(
                NAME,
                Verdict.FAIL,
                f"{len(removed_defs) - len(added_defs)} test case(s) removed without replacement",
                [
                    Evidence(
                        "git",
                        "test definitions removed",
                        {"removed": len(removed_defs), "added": len(added_defs)},
                    )
                ],
            )
        )

    new_skips = [ln for ln in added if SKIP_ADDED_RE.search(ln)]
    if new_skips:
        findings.append(
            IntegrityFinding(
                NAME,
                Verdict.FAIL,
                f"{len(new_skips)} new skip/xfail/only marker(s) added",
                [Evidence("git", "skip markers added", {"count": len(new_skips)})],
            )
        )

    weakened = [
        ln
        for ln in added
        if LOOSE_MATCHER_RE.search(ln)
        and any(EXACT_MATCHER_RE.search(r) and len(r.strip()) > 12 for r in removed)
    ]
    if weakened and not justified:
        findings.append(
            IntegrityFinding(
                NAME,
                Verdict.FAIL,
                "assertion weakened (exact matcher replaced with a loose one)",
                [Evidence("git", "weakened assertion", {"sample": weakened[0].strip()[:120]})],
            )
        )

    return findings
