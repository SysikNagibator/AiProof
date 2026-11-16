"""About screen."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text

from aiproof import version_string
from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.tui.logo import logo
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Text:
    """Render the About screen."""
    text = Text()
    text.append_text(logo(theme, ascii_only=ascii_only))
    text.append("\n")
    text.append(version_string() + "\n")
    text.append(t("tagline", lang) + "\n")
    text.append(t("about.license", lang))
    return text
