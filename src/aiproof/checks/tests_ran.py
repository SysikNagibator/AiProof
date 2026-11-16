"""Check: claimed test runs really happened, and counts match."""

from __future__ import annotations

import re
from dataclasses import dataclass

from aiproof.checks.base import CheckContext, failed, passed, unknown
from aiproof.claims.model import CheckResult, Claim, ClaimType, Evidence

NAME = "tests_ran"

TEST_CMD_RE = re.compile(
    r"\b(pytest|unittest|nosetests|jest|vitest|mocha|jasmine|ava|tape|"
    r"go test|cargo test|rspec|phpunit|dotnet test|mvn test|gradle test|"
    r"npm (?:run )?test|yarn test|pnpm test|bun test|make test|tox|nox)\b",
    re.IGNORECASE,
)
NO_TESTS_RE = re.compile(r"no tests ran|collected 0 items|0 tests|no test files", re.IGNORECASE)

_COUNT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("passed", re.compile(r"(\d+)\s+passed", re.IGNORECASE)),
    ("failed", re.compile(r"(\d+)\s+failed", re.IGNORECASE)),
    ("skipped", re.compile(r"(\d+)\s+skipped", re.IGNORECASE)),
    ("errors", re.compile(r"(\d+)\s+errors?", re.IGNORECASE)),
    ("examples", re.compile(r"(\d+)\s+examples?", re.IGNORECASE)),
    ("failures", re.compile(r"(\d+)\s+failures?", re.IGNORECASE)),
    ("dotnet_passed", re.compile(r"Passed!.*?Passed:\s*(\d+)", re.IGNORECASE)),
)


@dataclass(slots=True)
class TestCounts:
    """Parsed test-run counters."""

    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    saw_any: bool = False

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors


def parse_counts(output: str) -> TestCounts:
    """Parse common test-runner summaries from *output*."""
    counts = TestCounts()
    for _name, pattern in _COUNT_PATTERNS:
        matches = pattern.findall(output)
        if not matches:
            continue
        value = int(matches[-1])
        counts.saw_any = True
        if _name in ("passed", "dotnet_passed"):
            counts.passed = max(counts.passed, value)
        elif _name == "failed":
            counts.failed = max(counts.failed, value)
        elif _name == "skipped":
            counts.skipped = max(counts.skipped, value)
        elif _name == "errors":
            counts.errors = max(counts.errors, value)
        elif _name == "examples":
            counts.passed = max(counts.passed, value)
        elif _name == "failures":
            counts.failed = max(counts.failed, value)
    return counts


def _outputs(ctx: CheckContext) -> list[tuple[str, str]]:
    """Return ``(command, output)`` pairs observed during the session."""
    pairs: list[tuple[str, str]] = []
    for record in ctx.events("tool_post", "test_run"):
        payload = record.get("payload", {})
        command = str(payload.get("command", ""))
        output = str(payload.get("output") or payload.get("stdout") or "")
        pairs.append((command, output))
    return pairs


def _is_strict(ctx: CheckContext) -> bool:
    return ctx.settings.strictness in ("enforce", "strict")


def applies(claim: Claim) -> bool:
    """This check handles ``tests_pass`` and ``tests_added`` claims."""
    return claim.type in (ClaimType.TESTS_PASS, ClaimType.TESTS_ADDED)


def check(claim: Claim, ctx: CheckContext) -> CheckResult:
    """Verify test claims against observed runs and their real counts."""
    if claim.type is ClaimType.TESTS_ADDED:
        return _check_added(claim, ctx)

    pairs = [(c, o) for c, o in _outputs(ctx) if TEST_CMD_RE.search(c)]
    if not pairs:
        if _is_strict(ctx):
            return failed(claim, "no test command was run during this session")
        return unknown(claim, "no test command observed")

    best = TestCounts()
    evidence: list[Evidence] = []
    for command, output in pairs:
        counts = parse_counts(output)
        if counts.saw_any:
            evidence.append(
                Evidence(
                    "test_run",
                    command,
                    {
                        "passed": counts.passed,
                        "failed": counts.failed,
                        "skipped": counts.skipped,
                        "errors": counts.errors,
                    },
                )
            )
        if counts.total > best.total:
            best = counts
    if not best.saw_any:
        strict = ctx.settings.strictness == "strict"
        if strict and any(NO_TESTS_RE.search(o) for _c, o in pairs):
            return failed(claim, "test run collected no tests", evidence)
        return unknown(claim, "could not parse test counts from runner output", evidence)

    if best.failed or best.errors:
        return failed(
            claim, f"last run shows {best.failed} failed / {best.errors} errors", evidence
        )

    claimed = claim.params.get("count")
    if isinstance(claimed, int) and best.passed < claimed:
        return failed(claim, f"claimed {claimed} tests, found {best.passed}", evidence)
    return passed(claim, f"{best.passed} tests passed", evidence)


def _check_added(claim: Claim, ctx: CheckContext) -> CheckResult:
    from aiproof import gitutil

    if ctx.start_commit is None:
        return unknown(claim, "no git baseline to compare added tests")
    added = gitutil.added_lines_since(ctx.root, ctx.start_commit)
    looks_like_test = any(
        re.search(r"\b(def test_|it\(|test\(|describe\(|func Test|@Test|#\[test\])", line)
        for line in added
    )
    if looks_like_test:
        return passed(claim, "new test definitions found in the diff")
    return failed(claim, "no new test definitions found in the diff")
