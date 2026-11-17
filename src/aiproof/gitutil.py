"""Thin, safe git plumbing helpers (argument lists, timeouts, no shell)."""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

TIMEOUT = 20


def run_git(root: Path, args: list[str]) -> tuple[int, str, str]:
    """Run ``git`` in *root*; return ``(returncode, stdout, stderr)``."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=os.fspath(root),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - env dependent
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def is_repo(root: Path) -> bool:
    """Return True when *root* is inside a git work tree."""
    rc, out, _ = run_git(root, ["rev-parse", "--is-inside-work-tree"])
    return rc == 0 and out.strip() == "true"


def head_commit(root: Path) -> str | None:
    """Return the current HEAD commit hash, or None when unavailable."""
    rc, out, _ = run_git(root, ["rev-parse", "HEAD"])
    return out.strip() if rc == 0 and out.strip() else None


def current_branch(root: Path) -> str | None:
    """Return the current branch name, or None when detached/unavailable."""
    rc, out, _ = run_git(root, ["symbolic-ref", "--short", "-q", "HEAD"])
    return out.strip() if rc == 0 and out.strip() else None


def commit_exists(root: Path, rev: str) -> bool:
    """Return True when *rev* resolves to a commit object."""
    rc, _, _ = run_git(root, ["cat-file", "-e", f"{rev}^{{commit}}"])
    return rc == 0


def commit_subject(root: Path, rev: str) -> str:
    """Return the subject line of a commit (empty when unknown)."""
    rc, out, _ = run_git(root, ["log", "-1", "--pretty=%s", rev])
    return out.strip() if rc == 0 else ""


def commit_files(root: Path, rev: str) -> set[str]:
    """Return the set of files touched by a commit."""
    rc, out, _ = run_git(root, ["show", "--pretty=", "--name-only", rev])
    if rc != 0:
        return set()
    return {line.strip() for line in out.splitlines() if line.strip()}


def commit_timestamp(root: Path, rev: str) -> int:
    """Return a commit's committer timestamp (unix seconds), or 0."""
    rc, out, _ = run_git(root, ["log", "-1", "--pretty=%ct", rev])
    if rc != 0:
        return 0
    try:
        return int(out.strip())
    except ValueError:
        return 0


def is_ancestor_of_head(root: Path, rev: str) -> bool:
    """Return True when *rev* is reachable from HEAD."""
    rc, _, _ = run_git(root, ["merge-base", "--is-ancestor", rev, "HEAD"])
    return rc == 0


def changed_files(root: Path) -> set[str]:
    """Return staged + unstaged + untracked (non-ignored) file paths."""
    files: set[str] = set()
    _, out, _ = run_git(root, ["status", "--porcelain", "--untracked-files=all"])
    for line in out.splitlines():
        if len(line) < 4:
            continue
        rest = line[3:]
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        files.add(rest.strip().strip('"'))
    return files


def tracked_changed_files(root: Path) -> set[str]:
    """Return tracked files that are staged/unstaged modified, added or deleted.

    Untracked (``??``) and ignored (``!!``) entries are excluded: without a session
    baseline a freshly created protected file (e.g. written by ``aiproof init``) must
    not be mistaken for an in-session modification.
    """
    files: set[str] = set()
    _, out, _ = run_git(root, ["status", "--porcelain"])
    for line in out.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        if code.strip() in {"??", "!!"}:
            continue
        rest = line[3:]
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        files.add(rest.strip().strip('"'))
    return files


def file_content(root: Path, path: str, rev: str | None = None) -> str | None:
    """Return a file's content at *rev* (or HEAD when None); None when absent."""
    target = f"{rev}:{path}" if rev is not None else f"HEAD:{path}"
    rc, out, _ = run_git(root, ["show", target])
    if rc != 0:
        return None
    return out


def file_sha256(path: Path) -> str:
    """Return the SHA-256 of a file's bytes, or empty string when unreadable."""
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


# Session-start snapshot bounds: keep SessionStart cheap and the ledger small.
# ``docs/ARCHITECTURE.md`` requires that a hook never scans the whole repository,
# so inside a work tree only working-tree changes are snapshotted.
SNAPSHOT_MAX_FILES = 1000
SNAPSHOT_MAX_BYTES = 2 * 1024 * 1024
_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".aiproof",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".tox",
        "dist",
        "build",
        ".idea",
        ".vscode",
    }
)


def candidate_files(root: Path, *, limit: int = SNAPSHOT_MAX_FILES) -> list[str]:
    """Return files worth snapshotting at session start, bounded by *limit*.

    In a work tree this is the set of working-tree changes (modified, staged,
    untracked), so no full repository scan is performed. Outside a work tree a
    bounded, ignore-aware walk is used instead.
    """
    if is_repo(root):
        return sorted(changed_files(root))[:limit]
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _IGNORED_DIRS)
        for name in sorted(filenames):
            try:
                rel = (Path(dirpath) / name).relative_to(root).as_posix()
            except ValueError:  # pragma: no cover - defensive
                continue
            found.append(rel)
            if len(found) >= limit:
                return found
    return found


def snapshot_files(root: Path, *, limit: int = SNAPSHOT_MAX_FILES) -> dict[str, str]:
    """Return ``{posix path: sha256}`` for the session-start candidate files."""
    snapshot: dict[str, str] = {}
    for rel in candidate_files(root, limit=limit):
        path = root / rel
        try:
            if not path.is_file() or path.stat().st_size > SNAPSHOT_MAX_BYTES:
                continue
        except OSError:  # pragma: no cover - unreadable
            continue
        digest = file_sha256(path)
        if digest:
            snapshot[rel] = digest
    return snapshot


@dataclass(slots=True)
class DiffHunk:
    """A minimal added/removed line summary for a file."""

    path: str
    added: list[str]
    removed: list[str]


def added_lines_since(root: Path, rev: str, paths: tuple[str, ...] = ()) -> list[str]:
    """Return added lines in the working tree relative to *rev*."""
    args = ["diff", "-U0", rev, "--", *paths] if paths else ["diff", "-U0", rev]
    rc, out, _ = run_git(root, args)
    if rc != 0:
        return []
    return [ln[1:] for ln in out.splitlines() if ln.startswith("+") and not ln.startswith("+++")]


def removed_lines_since(root: Path, rev: str, paths: tuple[str, ...] = ()) -> list[str]:
    """Return removed lines in the working tree relative to *rev*."""
    args = ["diff", "-U0", rev, "--", *paths] if paths else ["diff", "-U0", rev]
    rc, out, _ = run_git(root, args)
    if rc != 0:
        return []
    return [ln[1:] for ln in out.splitlines() if ln.startswith("-") and not ln.startswith("---")]
