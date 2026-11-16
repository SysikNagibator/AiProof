"""Check: a claimed commit really exists, is reachable and touches claimed files."""

from __future__ import annotations

from aiproof import gitutil
from aiproof.checks.base import CheckContext, failed, passed, unknown
from aiproof.claims.model import CheckResult, Claim, ClaimType, Evidence

NAME = "commit_exists"


def applies(claim: Claim) -> bool:
    """This check handles ``committed`` claims."""
    return claim.type is ClaimType.COMMITTED


def check(claim: Claim, ctx: CheckContext) -> CheckResult:
    """Verify the claimed commit against the git object store."""
    if not gitutil.is_repo(ctx.root):
        return unknown(claim, "not a git repository")

    rev = claim.params.get("hash")
    claimed_files = claim.params.get("files") or []
    evidence: list[Evidence] = []

    if isinstance(rev, str):
        if not gitutil.commit_exists(ctx.root, rev):
            return failed(claim, f"no commit object for {rev}", evidence)
        evidence.append(Evidence("git", f"commit {rev} exists", {"rev": rev}))
        if not gitutil.is_ancestor_of_head(ctx.root, rev):
            return failed(claim, f"commit {rev} is not reachable from the current branch", evidence)
        commit_files = gitutil.commit_files(ctx.root, rev)
        if claimed_files:
            missing = [f for f in claimed_files if f not in commit_files]
            if missing:
                return failed(
                    claim,
                    f"commit {rev} does not touch claimed file(s): {', '.join(missing)}",
                    evidence,
                )
        return passed(claim, f"commit {rev} verified", evidence)

    head = gitutil.head_commit(ctx.root)
    if head is None:
        return failed(claim, "no HEAD commit exists", evidence)
    if ctx.start_commit is not None and head == ctx.start_commit:
        return failed(claim, "HEAD is unchanged since session start (no new commit)", evidence)
    evidence.append(Evidence("git", f"HEAD {head} is new since session start", {"head": head}))
    return passed(claim, f"new commit {head} present", evidence)
