"""Human-only pause / resume (an agent can never trigger these)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from aiproof import paths
from aiproof.guard.pin import require_human
from aiproof.ledger.store import LedgerStore

STATE_FILE = "state.json"


def _state_path(root: Path) -> Path:
    return paths.project_dir(root) / STATE_FILE


def _read_state(root: Path) -> dict[str, Any]:
    path = _state_path(root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(root: Path, state: dict[str, Any]) -> None:
    path = _state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def is_paused(root: Path) -> bool:
    """Return True when a pause window is currently active."""
    state = _read_state(root)
    until = state.get("paused_until")
    return isinstance(until, (int, float)) and until > time.time()


def pause(root: Path, minutes: int, *, session: str = "human") -> int:
    """Pause verification for *minutes* (human-only). Returns the until epoch."""
    require_human("pause")
    until = int(time.time()) + minutes * 60
    _write_state(root, {"paused_until": until, "minutes": minutes})
    LedgerStore(root).append("pause", {"minutes": minutes, "until": until}, session=session)
    return until


def resume(root: Path, *, session: str = "human") -> None:
    """Resume verification (human-only)."""
    require_human("resume")
    state = _read_state(root)
    state.pop("paused_until", None)
    _write_state(root, state)
    LedgerStore(root).append("resume", {}, session=session)
