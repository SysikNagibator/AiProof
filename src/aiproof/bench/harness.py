"""Benchmark harness: temp fixture repos and check contexts."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiproof.checks.base import CheckContext
from aiproof.claims.extractor import extract_claims
from aiproof.claims.model import Claim, ClaimType
from aiproof.config import Settings

ScenarioFn = "Callable[[Path], tuple[bool, bool, str]]"


@dataclass(slots=True)
class Outcome:
    """One scenario result."""

    index: int
    name: str
    blocked: bool
    expected_block: bool
    latency_ms: float
    note: str = ""

    @property
    def caught(self) -> bool:
        return self.blocked == self.expected_block


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in *root* (helper for fixtures)."""
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def make_repo(tmp: Path, files: dict[str, str] | None = None) -> tuple[Path, str | None]:
    """Init a repo, write *files*, commit a baseline; return ``(root, head)``."""
    tmp.mkdir(parents=True, exist_ok=True)
    git(tmp, "init", "-q")
    git(tmp, "config", "user.email", "bench@aiproof")
    git(tmp, "config", "user.name", "bench")
    (tmp / "src").mkdir(exist_ok=True)
    (tmp / "src" / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    for rel, content in (files or {}).items():
        target = tmp / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    git(tmp, "add", "-A")
    git(tmp, "commit", "-qm", "init")
    head = git(tmp, "rev-parse", "HEAD").stdout.strip() or None
    return tmp, head


def rec(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Build a synthetic ledger record for a check context."""
    return {"event": event, "payload": payload}


def tool_post(command: str, output: str) -> dict[str, Any]:
    """Build a ``tool_post`` record from a command and its output."""
    return rec("tool_post", {"command": command, "output": output})


def manual(
    claim_type: ClaimType, text: str, params: dict[str, Any] | None = None, lang: str = "en"
) -> Claim:
    """Build a claim directly (for precise scenarios)."""
    return Claim(
        type=claim_type, text=text, span=(0, len(text)), language=lang, params=params or {}
    )


def make_ctx(
    root: Path,
    *,
    claims_text: str = "",
    claims: list[Claim] | None = None,
    strictness: str = "enforce",
    start_commit: str | None = None,
    records: list[dict[str, Any]] | None = None,
) -> CheckContext:
    """Build a :class:`CheckContext` for a scenario."""
    resolved = list(claims) if claims is not None else extract_claims(claims_text)
    settings = Settings(strictness=strictness)
    return CheckContext(
        root=root,
        settings=settings,
        session="bench",
        start_commit=start_commit,
        records=records or [],
        claims=resolved,
    )
