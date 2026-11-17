"""Check: claimed files really changed since the session snapshot."""

from __future__ import annotations

from aiproof import gitutil
from aiproof.checks.base import CheckContext, failed, passed, unknown
from aiproof.claims.model import CheckResult, Claim, ClaimType, Evidence

NAME = "file_changed"

_FILEY = (ClaimType.FILE_WRITTEN, ClaimType.FILE_CHANGED, ClaimType.FILE_DELETED)


def applies(claim: Claim) -> bool:
    """This check handles file written/changed/deleted claims."""
    return claim.type in _FILEY


def _snapshot(ctx: CheckContext) -> dict[str, str]:
    for record in ctx.events("file_snapshot"):
        payload = record.get("payload", {})
        files = payload.get("files")
        if isinstance(files, dict):
            return {str(k): str(v) for k, v in files.items()}
    return {}


def check(claim: Claim, ctx: CheckContext) -> CheckResult:
    """Compare claimed files against the session-start content hashes."""
    files = claim.params.get("files")
    if not isinstance(files, list) or not files:
        return unknown(claim, "claim did not name any file")

    snapshot = _snapshot(ctx)
    changed = gitutil.changed_files(ctx.root)
    evidence: list[Evidence] = []
    missing: list[str] = []

    for raw in files:
        name = str(raw).replace("\\", "/")
        path = ctx.root / name
        current = gitutil.file_sha256(path)
        if name in snapshot:
            # Authoritative for files that already differed from HEAD at session
            # start: otherwise a dirty working tree would let an unchanged file
            # pass on the ``changed`` / ``start_commit`` fallbacks below.
            if current != snapshot[name]:
                evidence.append(
                    Evidence("snapshot", f"{name} differs from session snapshot", {"file": name})
                )
            else:
                missing.append(name)
            continue
        if name in changed:
            evidence.append(Evidence("git", f"{name} changed in working tree", {"file": name}))
            continue
        if ctx.start_commit is not None:
            baseline = gitutil.file_content(ctx.root, name, ctx.start_commit)
            now = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None
            if baseline != now:
                evidence.append(
                    Evidence("git", f"{name} differs from {ctx.start_commit}", {"file": name})
                )
                continue
        missing.append(name)

    if missing:
        verb = "deleted" if claim.type is ClaimType.FILE_DELETED else "changed"
        return failed(claim, f"claimed file(s) not {verb}: {', '.join(missing)}", evidence)
    return passed(claim, "claimed file changes verified", evidence)
