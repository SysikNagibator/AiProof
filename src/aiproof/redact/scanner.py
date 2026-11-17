"""Scanning git diffs, working trees, instruction files and agent histories."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from aiproof.adapters.registry import INSTRUCTION_FILES
from aiproof.redact.redactor import Allowlist, Finding, find_secrets, redact_text


@dataclass(slots=True)
class ScanFinding:
    """A secret finding with its location (never the value)."""

    path: str
    type: str
    fingerprint: str
    line: int = 0
    entropy: bool = False

    def as_dict(self) -> dict[str, object]:
        """Return a ledger-safe mapping."""
        return {
            "path": self.path,
            "type": self.type,
            "fingerprint": self.fingerprint,
            "line": self.line,
            "entropy": self.entropy,
        }


def _run_git(root: Path, args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=os.fspath(root),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout


def scan_text(text: str, location: str, allowlist: Allowlist | None = None) -> list[ScanFinding]:
    """Scan a blob of text, mapping each finding to ``location``."""
    if allowlist is not None and allowlist.allows_path(location):
        return []
    out: list[ScanFinding] = []
    line_of = _line_index(text)
    for finding in find_secrets(text, allowlist):
        out.append(
            ScanFinding(
                path=location,
                type=finding.type,
                fingerprint=finding.fingerprint,
                line=_line_for(line_of, finding.start),
                entropy=finding.entropy,
            )
        )
    return out


def _line_index(text: str) -> list[int]:
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _line_for(offsets: list[int], pos: int) -> int:
    lo, hi = 0, len(offsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offsets[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def scan_diff(root: Path, allowlist: Allowlist | None = None) -> list[ScanFinding]:
    """Scan staged, unstaged and untracked changes via git plumbing."""
    findings: list[ScanFinding] = []
    for args in (["diff", "-U0"], ["diff", "--cached", "-U0"]):
        diff = _run_git(root, args)
        if diff:
            findings.extend(scan_text(diff, "<git-diff>", allowlist))
    untracked = _run_git(root, ["ls-files", "--others", "--exclude-standard"])
    for rel in untracked.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        findings.extend(scan_file(root / rel, root, allowlist))
    return findings


def scan_file(
    path: Path, root: Path | None = None, allowlist: Allowlist | None = None
) -> list[ScanFinding]:
    """Scan a single file, mapping findings to a repo-relative path."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if root is not None:
        try:
            location = os.fspath(path.relative_to(root))
        except ValueError:
            location = os.fspath(path)
    else:
        location = os.fspath(path)
    return scan_text(text, location.replace(os.sep, "/"), allowlist)


def iter_tracked(root: Path) -> list[Path]:
    """Return tracked files plus non-ignored untracked files."""
    output = _run_git(root, ["ls-files", "--cached", "--others", "--exclude-standard"])
    files: list[Path] = []
    for rel in output.splitlines():
        rel = rel.strip()
        if rel:
            files.append(root / rel)
    return files


def scan_tree(root: Path, allowlist: Allowlist | None = None) -> list[ScanFinding]:
    """Scan every tracked/non-ignored file in the working tree."""
    findings: list[ScanFinding] = []
    for path in iter_tracked(root):
        findings.extend(scan_file(path, root, allowlist))
    return findings


def scan_instruction_files(root: Path, allowlist: Allowlist | None = None) -> list[ScanFinding]:
    """Scan agent instruction/rule files for hard-coded keys."""
    findings: list[ScanFinding] = []
    for rel in INSTRUCTION_FILES:
        candidate = root / rel
        if candidate.is_dir():
            for child in candidate.rglob("*.md"):
                findings.extend(scan_file(child, root, allowlist))
        elif candidate.is_file():
            findings.extend(scan_file(candidate, root, allowlist))
    return findings


# Agent history/memory locations. VERIFY against vendor docs before extending;
# these are best-effort and always optional (report-only).
def agent_history_paths() -> list[Path]:
    """Return known agent history/memory files to scan (best effort)."""
    home = Path.home()
    candidates = [
        home / ".claude" / "history.jsonl",
        home / ".claude.json",
        home / ".codex" / "history.jsonl",
        home / ".gemini" / "history.jsonl",
        home / ".aider" / "history",
    ]
    return [p for p in candidates if p.is_file()]


def scan_agent_histories(allowlist: Allowlist | None = None) -> list[ScanFinding]:
    """Scan known agent history/memory files (report-only)."""
    findings: list[ScanFinding] = []
    for path in agent_history_paths():
        findings.extend(scan_file(path, None, allowlist))
    return findings


def redact_in_place(path: Path, allowlist: Allowlist | None = None) -> tuple[bool, str]:
    """Redact a file in place with a ``.bak`` backup; returns ``(changed, backup)``."""
    try:
        original = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return False, f"cannot read: {exc}"
    redacted = redact_text(original, allowlist)
    if redacted == original:
        return False, ""
    backup = path.with_suffix(path.suffix + ".bak")
    try:
        backup.write_text(original, encoding="utf-8")
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(redacted, encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        return False, f"write failed: {exc}"
    return True, os.fspath(backup)


# Re-export for convenience.
__all__ = [
    "Finding",
    "ScanFinding",
    "agent_history_paths",
    "redact_in_place",
    "scan_agent_histories",
    "scan_diff",
    "scan_file",
    "scan_instruction_files",
    "scan_text",
    "scan_tree",
]
