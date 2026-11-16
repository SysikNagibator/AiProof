"""Human-only actions and pin verification."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from aiproof.config import Settings, pinned_ok, write_pinned


class HumanOnlyError(RuntimeError):
    """Raised when an action attempted outside an interactive human TTY."""


def is_interactive() -> bool:
    """Return True only for a genuine interactive human terminal."""
    if os.environ.get("AIPROOF_NON_INTERACTIVE") == "1":
        return False
    if os.environ.get("CI"):
        return False
    # A parent heuristic: agents typically run hooks with closed/piped stdio.
    return sys.stdin.isatty() and sys.stdout.isatty()


def require_human(action: str) -> None:
    """Raise :class:`HumanOnlyError` unless an interactive human runs this."""
    if not is_interactive():
        raise HumanOnlyError(
            f"'{action}' requires an interactive human terminal; agents cannot run it."
        )


def verify_pins(root: Path) -> tuple[bool, str]:
    """Return ``(ok, reason)`` for pinned-config integrity."""
    return pinned_ok(root)


def repin(root: Path, settings: Settings) -> str:
    """Re-pin settings (human-only) and return the new digest."""
    require_human("pin")
    pinned = write_pinned(root, settings)
    return pinned.sha256
