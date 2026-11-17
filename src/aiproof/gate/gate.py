"""Gate decision logic for the agent Stop hook."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aiproof.checks import claim_checks_for, integrity_checks
from aiproof.checks.base import CheckContext, IntegrityFinding
from aiproof.claims.model import CheckResult, Verdict
from aiproof.gate import messages


@dataclass(slots=True)
class GateDecision:
    """The outcome of evaluating one Stop event."""

    block: bool
    strictness: str
    reason: str = ""
    results: list[CheckResult] = field(default_factory=list)
    findings: list[IntegrityFinding] = field(default_factory=list)
    capped: bool = False

    def counts(self) -> dict[str, int]:
        """Return verdict counters for the ledger."""
        fails = sum(1 for r in self.results if r.verdict is Verdict.FAIL)
        fails += sum(1 for f in self.findings if f.verdict is Verdict.FAIL)
        unknowns = sum(1 for r in self.results if r.verdict is Verdict.UNKNOWN)
        unknowns += sum(1 for f in self.findings if f.verdict is Verdict.UNKNOWN)
        return {
            "checks": len(self.results) + len(self.findings),
            "fail": fails,
            "unknown": unknowns,
        }

    def as_dict(self) -> dict[str, Any]:
        """Return a ledger-safe mapping."""
        return {
            "block": self.block,
            "strictness": self.strictness,
            "capped": self.capped,
            "reason": self.reason,
            "results": [r.as_dict() for r in self.results],
            "findings": [f.as_dict() for f in self.findings],
            "counts": self.counts(),
        }


def decide(
    ctx: CheckContext,
    *,
    agent_lang: str = "en",
    capped: bool = False,
    integrity: bool = True,
) -> GateDecision:
    """Run the relevant checks and decide whether to block the stop.

    ``integrity=False`` runs only per-claim checks (used for ad-hoc self-checks that
    have no session baseline, so whole-session integrity checks cannot decide).
    """
    enabled = ctx.settings.enabled_checks
    strictness = ctx.settings.strictness

    results: list[CheckResult] = []
    for claim in ctx.claims:
        for module in claim_checks_for(claim):
            if module.NAME in enabled:
                results.append(module.check(claim, ctx))

    findings: list[IntegrityFinding] = []
    if integrity:
        for module in integrity_checks(enabled):
            findings.extend(module.run(ctx))

    has_fail = any(r.verdict is Verdict.FAIL for r in results) or any(
        f.verdict is Verdict.FAIL for f in findings
    )
    has_unknown = any(r.verdict is Verdict.UNKNOWN for r in results) or any(
        f.verdict is Verdict.UNKNOWN for f in findings
    )

    decision = GateDecision(
        block=False,
        strictness=strictness,
        results=results,
        findings=findings,
        capped=capped,
    )

    if capped:
        # Safety valve: after MAX_BLOCKS consecutive blocks (or when the agent
        # reports ``stop_hook_active``) never block again. Otherwise an agent that
        # cannot satisfy a check would be trapped in an endless Stop-hook loop.
        decision.block = False
    elif strictness in ("observe", "warn"):
        decision.block = False
    elif strictness == "strict":
        decision.block = has_fail or has_unknown
    else:  # enforce
        decision.block = has_fail

    if decision.block or strictness in ("warn", "strict"):
        decision.reason = messages.build(decision, ctx, agent_lang)
    return decision
