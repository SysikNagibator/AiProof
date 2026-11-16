"""Wrapper mode: ``aiproof run -- <agent command>`` (post-hoc verification)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aiproof import gitutil
from aiproof.checks import claim_checks_for, integrity_checks
from aiproof.checks.base import CheckContext
from aiproof.claims.extractor import extract_claims
from aiproof.claims.model import Verdict
from aiproof.config import load_settings
from aiproof.gate import messages
from aiproof.gate.gate import decide


def run_wrapped(argv: list[str], root: Path) -> int:
    """Run an agent command, then verify its claims post-hoc (cannot block)."""
    if not argv:
        print("usage: aiproof run -- <agent command>", file=sys.stderr)
        return 2

    settings = load_settings(root)
    start_commit = gitutil.head_commit(root) if gitutil.is_repo(root) else None
    start_ts = int(__import__("time").time())

    proc = subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)

    claims = extract_claims(output)
    ctx = CheckContext(
        root=root,
        settings=settings,
        session="wrapper",
        start_commit=start_commit,
        start_ts=start_ts,
        records=[],
        claims=claims,
    )
    decision = decide(ctx, agent_lang=settings.agent_message_language)
    _ = (claim_checks_for, integrity_checks)  # registry imported for side-effect parity

    print("\n--- AiProof (wrapper, post-hoc) ---")
    if not claims:
        print("No verifiable claims found in the agent output.")
    for result in decision.results:
        mark = {Verdict.PASS: "PASS", Verdict.FAIL: "FAIL", Verdict.UNKNOWN: "UNKNOWN"}[
            result.verdict
        ]
        print(f"[{mark}] {result.claim.type}: {result.reason}")
    for finding in decision.findings:
        if finding.verdict is Verdict.FAIL:
            print(f"[FAIL] {finding.check}: {finding.reason}")
    if decision.block:
        print(messages.build(decision, ctx, settings.agent_message_language))
    return proc.returncode
