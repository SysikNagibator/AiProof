"""Integrity check: pinned config and protected agent files unchanged."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from aiproof import gitutil, paths
from aiproof.checks.base import CheckContext, IntegrityFinding
from aiproof.claims.model import Evidence, Verdict
from aiproof.config import pinned_ok

NAME = "config_integrity"


def _expand(pattern: str) -> str:
    return pattern.replace("{data}", str(paths.data_dir())).replace("\\", "/")


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    candidate = path.replace("\\", "/")
    for pattern in patterns:
        expanded = _expand(pattern)
        if fnmatch.fnmatch(candidate, expanded):
            return True
        # Editor tools send absolute paths; a repo-relative protected pattern must
        # still match them, so also try the pattern anchored at any directory.
        if not expanded.startswith(("**", "/")) and fnmatch.fnmatch(candidate, "**/" + expanded):
            return True
    return False


def protected_path(path: Path, settings_patterns: tuple[str, ...]) -> bool:
    """Return True when *path* is protected (used by the tamper guard)."""
    return _matches(str(path), settings_patterns)


def protected_files(root: Path, patterns: tuple[str, ...]) -> dict[str, str]:
    """Return ``{repo-relative path: sha256}`` for every existing protected file.

    Only repo-relative glob patterns are expanded (data-dir patterns live outside
    the repo and are covered by the pinned-config self-hash instead).
    """
    found: dict[str, str] = {}
    for pattern in patterns:
        if "{data}" in pattern:
            continue
        rel_pattern = pattern.replace("\\", "/").lstrip("/")
        for path in root.glob(rel_pattern):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:  # pragma: no cover - defensive
                continue
            found[rel] = gitutil.file_sha256(path)
    return found


def _snapshot(ctx: CheckContext) -> dict[str, str] | None:
    """Return the session-start protected snapshot, or ``None`` when absent."""
    for record in ctx.events("session_start"):
        payload = record.get("payload", {})
        if isinstance(payload, dict) and isinstance(payload.get("protected_files"), dict):
            return {str(k): str(v) for k, v in payload["protected_files"].items()}
    return None


def _tampered_files(ctx: CheckContext) -> list[str]:
    """Return protected files that changed during the session.

    With a session-start snapshot we compare content hashes (so files created by
    ``aiproof init`` before the session are not false positives). Without one we
    fall back to comparing against git's working-tree status.
    """
    protected = ctx.settings.protected_paths
    snapshot = _snapshot(ctx)
    if snapshot is not None:
        current = protected_files(ctx.root, protected)
        changed = [
            rel for rel, digest in current.items() if rel in snapshot and snapshot[rel] != digest
        ]
        changed += [rel for rel in snapshot if rel not in current]  # deleted
        changed += [rel for rel in current if rel not in snapshot]  # created in-session
        return sorted(set(changed))
    return [f for f in gitutil.tracked_changed_files(ctx.root) if _matches(f, protected)]


def run(ctx: CheckContext) -> list[IntegrityFinding]:
    """Verify pin integrity and block agent writes to protected configuration."""
    findings: list[IntegrityFinding] = []

    ok, reason = pinned_ok(ctx.root)
    if not ok and "missing" not in reason:
        findings.append(
            IntegrityFinding(NAME, Verdict.FAIL, f"pinned config integrity failure: {reason}")
        )

    changed = gitutil.changed_files(ctx.root)
    tampered = _tampered_files(ctx)
    if tampered:
        findings.append(
            IntegrityFinding(
                NAME,
                Verdict.FAIL,
                f"protected config file(s) modified during session: {', '.join(sorted(tampered))}",
                [Evidence("git", "protected file changed", {"files": sorted(tampered)})],
            )
        )

    if ctx.settings.protect_ci:
        ci = [f for f in changed if f.startswith(".github/workflows/") or f in {".gitlab-ci.yml"}]
        if ci:
            findings.append(
                IntegrityFinding(
                    NAME, Verdict.FAIL, f"CI config modified while protect_ci=true: {', '.join(ci)}"
                )
            )
    return findings
