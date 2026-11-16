"""Integrity check: enabled correction rules compiled from human feedback."""

from __future__ import annotations

from aiproof import gitutil, paths
from aiproof.checks.base import CheckContext, IntegrityFinding
from aiproof.claims.model import Evidence, Verdict
from aiproof.learn.dsl import DiffFile, RuleHit, apply_rules, load_rules

NAME = "learn_rules"


def _diff_files(ctx: CheckContext) -> list[DiffFile]:
    """Return added lines per changed/untracked file since the session start."""
    if ctx.start_commit is None:
        return []
    files: list[DiffFile] = []
    rc, out, _ = gitutil.run_git(ctx.root, ["diff", "--name-only", ctx.start_commit])
    if rc == 0:
        for path in sorted({line.strip() for line in out.splitlines() if line.strip()}):
            added = gitutil.added_lines_since(ctx.root, ctx.start_commit, paths=(path,))
            if added:
                files.append(DiffFile(path, tuple(added)))
    rc, out, _ = gitutil.run_git(ctx.root, ["ls-files", "--others", "--exclude-standard"])
    if rc == 0:
        for rel in sorted({line.strip() for line in out.splitlines() if line.strip()}):
            try:
                text = (ctx.root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            files.append(DiffFile(rel, tuple(text.splitlines())))
    return files


def _finding(rule_id: str, hits: list[RuleHit]) -> IntegrityFinding:
    first = hits[0]
    verdict = Verdict.FAIL if first.severity == "block" else Verdict.UNKNOWN
    evidence = [
        Evidence(
            "rule",
            f"{hit.path}:{hit.line} {hit.text}".strip(),
            hit.as_dict(),
        )
        for hit in hits[:5]
    ]
    return IntegrityFinding(
        NAME,
        verdict,
        f"rule {rule_id} matched {len(hits)} time(s): {first.description}",
        evidence,
    )


def run(ctx: CheckContext) -> list[IntegrityFinding]:
    """Evaluate enabled rules against the diff and this session's commands."""
    rules = load_rules(paths.rules_path(ctx.root))
    if not rules:
        return []
    hits = apply_rules(rules, _diff_files(ctx), ctx.commands())
    grouped: dict[str, list[RuleHit]] = {}
    for hit in hits:
        grouped.setdefault(hit.rule_id, []).append(hit)
    return [_finding(rule_id, rule_hits) for rule_id, rule_hits in grouped.items()]


__all__ = ["NAME", "run"]
