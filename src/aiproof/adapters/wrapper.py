"""Wrapper mode: ``aiproof run -- <agent command>`` (post-hoc verification)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from aiproof import gitutil
from aiproof.checks import claim_checks_for, integrity_checks
from aiproof.checks.base import CheckContext
from aiproof.claims.extractor import extract_claims
from aiproof.claims.model import Verdict
from aiproof.config import load_settings
from aiproof.gate import messages
from aiproof.gate.gate import decide
from aiproof.i18n import detect_language, t


def run_wrapped(argv: list[str], root: Path) -> int:
    """Run an agent command, then verify its claims post-hoc (cannot block)."""
    command = list(argv)
    # argparse.REMAINDER keeps the literal ``--``; drop a single leading one.
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print(t("wrap.usage", detect_language()), file=sys.stderr)
        return 2

    settings = load_settings(root)
    lang = detect_language()
    start_commit = gitutil.head_commit(root) if gitutil.is_repo(root) else None
    start_ts = int(__import__("time").time())

    # Snapshot protected files BEFORE the wrapped command so config_integrity can
    # compare like-for-like (wrapper mode has no real SessionStart hook).
    from aiproof.checks.config_integrity import protected_files

    baseline = protected_files(root, settings.protected_paths)
    session_records: list[dict[str, Any]] = [
        {
            "event": "session_start",
            "payload": {"start_commit": start_commit, "protected_files": baseline},
        },
        {
            "event": "file_snapshot",
            "payload": {"files": gitutil.snapshot_files(root)},
        },
    ]

    try:
        proc = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        print(t("wrap.cannot_run", lang, command=repr(command[0]), error=exc), file=sys.stderr)
        return 127
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
        records=session_records,
        claims=claims,
    )
    decision = decide(ctx, agent_lang=settings.agent_message_language)
    _ = (claim_checks_for, integrity_checks)  # registry imported for side-effect parity

    print("\n" + t("wrap.header", lang))
    if not claims:
        print(t("wrap.no_claims", lang))
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
    # The wrapped agent has already exited, so nothing is blocked mid-session. The
    # exit code still reflects the verdict: a non-zero agent status wins, otherwise a
    # blocking verdict returns 1 so CI can act on it.
    if proc.returncode != 0:
        return proc.returncode
    return 1 if decision.block else 0
