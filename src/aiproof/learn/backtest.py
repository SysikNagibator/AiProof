"""Backtest a rule against stored history before enabling it.

The replay uses the repository's git history (added lines) plus the commands
recorded in AiProof's ledger. We cannot know a *true* false positive without
labelled data, so ``false_positives`` counts explicit ``aiproof:ignore`` waivers
(a lower bound) and the result carries a note saying so.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiproof import gitutil
from aiproof.learn.dsl import DiffFile, Rule, RuleHit, apply_rule
from aiproof.ledger.store import LedgerStore

DEFAULT_LIMIT = 200


@dataclass(frozen=True, slots=True)
class HistoryCommit:
    """One commit from local history with its added lines."""

    rev: str
    subject: str
    files: tuple[DiffFile, ...]


@dataclass(slots=True)
class BacktestResult:
    """Aggregated replay numbers for one rule."""

    rule_id: str
    commits_scanned: int
    would_have_caught: int
    false_positives: int
    samples: list[dict[str, Any]]
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe mapping."""
        return {
            "rule": self.rule_id,
            "commits_scanned": self.commits_scanned,
            "would_have_caught": self.would_have_caught,
            "false_positives": self.false_positives,
            "samples": self.samples,
            "note": self.note,
        }


def _parse_added(show: str) -> tuple[DiffFile, ...]:
    files: list[DiffFile] = []
    path: str | None = None
    added: list[str] = []
    for line in show.splitlines():
        if line.startswith("+++ "):
            if path is not None:
                files.append(DiffFile(path, tuple(added)))
            target = line[4:].strip()
            path = None if target == "/dev/null" else target.removeprefix("b/")
            added = []
        elif line.startswith("+") and not line.startswith("+++") and path is not None:
            added.append(line[1:])
    if path is not None:
        files.append(DiffFile(path, tuple(added)))
    return tuple(files)


def collect_history(root: Path, limit: int = DEFAULT_LIMIT) -> list[HistoryCommit]:
    """Return up to *limit* non-merge commits with their added lines."""
    if not gitutil.is_repo(root):
        return []
    rc, out, _ = gitutil.run_git(root, ["log", f"-n{limit}", "--no-merges", "--format=%H"])
    if rc != 0:
        return []
    commits: list[HistoryCommit] = []
    for rev in (line.strip() for line in out.splitlines()):
        if not rev:
            continue
        rc_show, show, _ = gitutil.run_git(
            root, ["show", "--format=", "--unified=0", "--no-color", rev]
        )
        if rc_show != 0:
            continue
        commits.append(
            HistoryCommit(
                rev=rev,
                subject=gitutil.commit_subject(root, rev),
                files=_parse_added(show),
            )
        )
    return commits


def collect_commands(root: Path) -> list[str]:
    """Return every shell command observed in the ledger."""
    commands: list[str] = []
    for record in LedgerStore(root).records():
        if record.get("event") not in ("tool_pre", "tool_post"):
            continue
        payload = record.get("payload", {})
        if not isinstance(payload, dict):
            continue
        command = payload.get("command")
        if isinstance(command, str) and command.strip():
            commands.append(command)
    return commands


def _sample(hit: RuleHit, context: str) -> dict[str, Any]:
    data = hit.as_dict()
    data["context"] = context
    return data


def backtest(root: Path, rule: Rule, limit: int = DEFAULT_LIMIT) -> BacktestResult:
    """Replay *rule* over local git history and recorded commands."""
    history = collect_history(root, limit)
    commands = collect_commands(root)
    would = 0
    false_positives = 0
    samples: list[dict[str, Any]] = []
    for commit in history:
        hits = apply_rule(rule, commit.files, include_waivers=True)
        real = [hit for hit in hits if not hit.waiver]
        false_positives += sum(1 for hit in hits if hit.waiver)
        if real:
            would += 1
            for hit in real[:2]:
                if len(samples) < 5:
                    samples.append(_sample(hit, f"{commit.rev[:8]} {commit.subject[:60]}"))

    command_hits = apply_rule(rule, (), commands, include_waivers=True)
    real_commands = [hit for hit in command_hits if not hit.waiver]
    false_positives += sum(1 for hit in command_hits if hit.waiver)
    if real_commands:
        would += 1
        for hit in real_commands[:2]:
            if len(samples) < 5:
                samples.append(_sample(hit, "ledger command"))

    return BacktestResult(
        rule_id=rule.id,
        commits_scanned=len(history),
        would_have_caught=would,
        false_positives=false_positives,
        samples=samples,
        note=(
            "false positives count explicit `aiproof:ignore` waivers only; "
            "true rate needs labelled history (see docs/LEARN.md)"
        ),
    )


__all__ = [
    "BacktestResult",
    "HistoryCommit",
    "backtest",
    "collect_commands",
    "collect_history",
]
