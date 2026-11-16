"""Check interface, context and registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from aiproof.claims.model import CheckResult, Claim, Evidence, Verdict
from aiproof.config import Settings


@dataclass(slots=True)
class IntegrityFinding:
    """A whole-session finding not tied to a single claim."""

    check: str
    verdict: Verdict
    reason: str
    evidence: list[Evidence] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Return a ledger-safe mapping."""
        return {
            "check": self.check,
            "verdict": str(self.verdict),
            "reason": self.reason,
            "evidence": [
                {"kind": e.kind, "detail": e.detail, "data": e.data} for e in self.evidence
            ],
        }


@dataclass(slots=True)
class CheckContext:
    """Everything a check may read (all local, all deterministic)."""

    root: Path
    settings: Settings
    session: str
    start_commit: str | None = None
    start_ts: int = 0
    records: list[dict[str, Any]] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)

    def events(self, *kinds: str) -> list[dict[str, Any]]:
        """Return ledger records whose ``event`` is one of *kinds*."""
        wanted = set(kinds)
        return [r for r in self.records if r.get("event") in wanted]

    def commands(self) -> list[str]:
        """Return every shell command observed this session."""
        out: list[str] = []
        for record in self.events("tool_pre", "tool_post"):
            payload = record.get("payload", {})
            cmd = payload.get("command")
            if isinstance(cmd, str):
                out.append(cmd)
        return out


class ClaimCheck(Protocol):
    """Protocol for a per-claim check module."""

    NAME: str

    def applies(self, claim: Claim) -> bool: ...

    def check(self, claim: Claim, ctx: CheckContext) -> CheckResult: ...


class IntegrityCheck(Protocol):
    """Protocol for a whole-session check module."""

    NAME: str

    def run(self, ctx: CheckContext) -> list[IntegrityFinding]: ...


ClaimCheckFn = Callable[[Claim, CheckContext], CheckResult]


def unknown(claim: Claim, reason: str, evidence: list[Evidence] | None = None) -> CheckResult:
    """Build an ``unknown`` result (never silently a pass)."""
    return CheckResult(claim=claim, verdict=Verdict.UNKNOWN, reason=reason, evidence=evidence or [])


def passed(claim: Claim, reason: str, evidence: list[Evidence] | None = None) -> CheckResult:
    """Build a ``pass`` result."""
    return CheckResult(claim=claim, verdict=Verdict.PASS, reason=reason, evidence=evidence or [])


def failed(claim: Claim, reason: str, evidence: list[Evidence] | None = None) -> CheckResult:
    """Build a ``fail`` result."""
    return CheckResult(claim=claim, verdict=Verdict.FAIL, reason=reason, evidence=evidence or [])
