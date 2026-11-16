"""Minimal append-only operational log (separate from the ledger)."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from aiproof import paths


def log(message: str, *, level: str = "info") -> None:
    """Append one line to ``~/.aiproof/aiproof.log`` (best effort)."""
    try:
        target = paths.log_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        with target.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} [{level}] {message}\n")
    except OSError:
        # Never let logging failures affect the agent.
        if os.environ.get("AIPROOF_DEBUG"):
            raise
