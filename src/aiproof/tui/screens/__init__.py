"""Screen registry."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from aiproof.config import Settings
from aiproof.tui.screens import (
    about,
    checks,
    dashboard,
    doctor,
    live_feed,
    logs,
    rules,
    secrets,
    session_detail,
    sessions,
    update,
)
from aiproof.tui.screens import (
    settings as settings_screen,
)
from aiproof.tui.theme import Theme

Renderer = Callable[[Path, Settings, str, Theme, bool], Any]

RENDERERS: dict[str, Renderer] = {
    "dashboard": dashboard.render,
    "live_feed": live_feed.render,
    "sessions": sessions.render,
    "session_detail": session_detail.render,
    "checks": checks.render,
    "secrets": secrets.render,
    "rules": rules.render,
    "settings": settings_screen.render,
    "doctor": doctor.render,
    "logs": logs.render,
    "update": update.render,
    "about": about.render,
}


def render(
    screen: str, root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool
) -> Any:
    """Render a screen by id (falls back to the dashboard)."""
    renderer = RENDERERS.get(screen, dashboard.render)
    return renderer(root, settings, lang, theme, ascii_only)
