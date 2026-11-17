"""Localized, specific, actionable gate messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiproof.checks.base import CheckContext
from aiproof.claims.model import ClaimType, Verdict
from aiproof.i18n import t

if TYPE_CHECKING:
    from aiproof.gate.gate import GateDecision


def _claim_detail(ctx: CheckContext, decision: GateDecision) -> str:
    """Return the first failing evidence detail for the tamper/config keys."""
    for finding in decision.findings:
        if finding.verdict is Verdict.FAIL:
            return finding.reason
    for result in decision.results:
        if result.verdict is Verdict.FAIL:
            return result.reason
    return ""


def build(decision: GateDecision, ctx: CheckContext, lang: str = "en") -> str:
    """Compose a specific block message from a decision, in *lang*."""
    if lang == "auto":
        from aiproof.i18n import detect_language

        lang = detect_language()
    lines: list[str] = [t("gate.header", lang)]

    for finding in decision.findings:
        if finding.verdict is not Verdict.FAIL:
            continue
        if finding.check == "test_tamper":
            lines.append("- " + t("gate.block.tamper_tests", lang, detail=finding.reason))
        elif finding.check == "secrets_in_diff":
            lines.append("- " + t("gate.block.secrets", lang, detail=finding.reason))
        elif finding.check == "todo_integrity":
            lines.append("- " + t("gate.block.todo", lang, detail=finding.reason))
        elif finding.check == "config_integrity":
            lines.append("- " + t("gate.block.config", lang, detail=finding.reason))
        elif finding.check == "learn_rules":
            lines.append("- " + t("gate.block.rule", lang, detail=finding.reason))

    for result in decision.results:
        if result.verdict is Verdict.PASS:
            continue
        verb = result.verdict
        claim = result.claim
        if claim.type is ClaimType.TESTS_PASS:
            if verb is Verdict.FAIL and "no test command" in result.reason:
                lines.append("- " + t("gate.block.tests_not_run", lang))
                continue
            claimed = claim.params.get("count")
            found = _first_int(result.reason)
            if isinstance(claimed, int) and found is not None:
                lines.append(
                    "- " + t("gate.block.tests_mismatch", lang, claimed=claimed, found=found)
                )
            else:
                lines.append("- " + t("gate.block.tamper_tests", lang, detail=result.reason))
        elif claim.type is ClaimType.COMMITTED and verb is Verdict.FAIL:
            lines.append("- " + t("gate.block.commit_missing", lang))
        elif (
            claim.type in (ClaimType.FILE_WRITTEN, ClaimType.FILE_CHANGED, ClaimType.FILE_DELETED)
            and verb is Verdict.FAIL
        ):
            files = claim.params.get("files") or [claim.text]
            lines.append("- " + t("gate.block.file_unchanged", lang, file=str(files[0])))
        elif verb is Verdict.FAIL or verb is Verdict.UNKNOWN:
            lines.append("- " + t("gate.block.unknown", lang, detail=result.reason))

    lines.append("")
    lines.append(t("gate.footer", lang))
    return "\n".join(lines)


def _first_int(text: str) -> int | None:
    import re

    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else None
