"""Claim / evidence / verdict data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ClaimType(StrEnum):
    """Kinds of verifiable claims an agent can make."""

    COMMITTED = "committed"
    PUSHED = "pushed"
    FILE_WRITTEN = "file_written"
    FILE_CHANGED = "file_changed"
    FILE_DELETED = "file_deleted"
    TESTS_PASS = "tests_pass"
    TESTS_ADDED = "tests_added"
    BUILD_PASSES = "build_passes"
    LINT_PASSES = "lint_passes"
    BUG_FIXED = "bug_fixed"
    FEATURE_DONE = "feature_done"
    DEPENDENCY_INSTALLED = "dependency_installed"
    MIGRATION_RUN = "migration_run"


class Verdict(StrEnum):
    """Verification verdict. ``unknown`` is never silently promoted to ``pass``."""

    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Rule:
    """A language-pack rule mapping phrases to a claim type."""

    claim: ClaimType
    patterns: tuple[str, ...]
    negations: tuple[str, ...] = ()
    hedges: tuple[str, ...] = ()


@dataclass(slots=True)
class Claim:
    """An extracted claim with provenance."""

    type: ClaimType
    text: str
    span: tuple[int, int]
    language: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Evidence:
    """A single piece of evidence backing a verdict."""

    kind: str
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CheckResult:
    """The outcome of a single check on a single claim."""

    claim: Claim
    verdict: Verdict
    reason: str = ""
    evidence: list[Evidence] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Return a ledger-safe mapping."""
        return {
            "claim": {
                "type": str(self.claim.type),
                "text": self.claim.text,
                "language": self.claim.language,
                "params": self.claim.params,
            },
            "verdict": str(self.verdict),
            "reason": self.reason,
            "evidence": [
                {"kind": e.kind, "detail": e.detail, "data": e.data} for e in self.evidence
            ],
        }
