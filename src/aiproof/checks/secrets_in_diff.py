"""Integrity check: secrets appearing in the diff / instruction files."""

from __future__ import annotations

from aiproof.checks.base import CheckContext, IntegrityFinding
from aiproof.claims.model import Evidence, Verdict
from aiproof.config import load_settings
from aiproof.paths import project_allow_path
from aiproof.redact.redactor import Allowlist, load_allowlist
from aiproof.redact.scanner import scan_diff, scan_instruction_files

NAME = "secrets_in_diff"


def _allowlist(ctx: CheckContext) -> Allowlist:
    allow = load_allowlist(project_allow_path(ctx.root))
    settings = load_settings(ctx.root) if not ctx.settings else ctx.settings
    if settings.allowlist_regexes:
        allow.regexes = allow.regexes + tuple(settings.allowlist_regexes)
    if settings.allowlist_paths:
        allow.paths = allow.paths + tuple(settings.allowlist_paths)
    allow.compile()
    return allow


def run(ctx: CheckContext) -> list[IntegrityFinding]:
    """Scan the working diff and instruction files for secrets (types only)."""
    allow = _allowlist(ctx)
    findings = scan_diff(ctx.root, allow)
    findings.extend(scan_instruction_files(ctx.root, allow))
    if not findings:
        return []
    by_type: dict[str, int] = {}
    for finding in findings:
        by_type[finding.type] = by_type.get(finding.type, 0) + 1
    evidence = [
        Evidence(
            "secret",
            f"{f.type} at {f.path}:{f.line} [{f.fingerprint}]",
            {"path": f.path, "line": f.line, "type": f.type, "fingerprint": f.fingerprint},
        )
        for f in findings[:20]
    ]
    return [
        IntegrityFinding(
            NAME,
            Verdict.FAIL,
            f"{len(findings)} secret finding(s): "
            + ", ".join(f"{t}×{n}" for t, n in sorted(by_type.items())),
            evidence,
        )
    ]
