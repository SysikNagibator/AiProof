"""Rules & Corrections screen: advisory corrections and compiled rules."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table

from aiproof import paths
from aiproof.config import Settings
from aiproof.i18n import t
from aiproof.learn.corrections import list_corrections
from aiproof.learn.dsl import load_rules
from aiproof.tui.theme import Theme


def render(root: Path, settings: Settings, lang: str, theme: Theme, ascii_only: bool) -> Table:
    """Render recorded corrections plus compiled rules and their state."""
    table = Table(title=t("menu.rules", lang), border_style=theme.primary)
    table.add_column("id", style=theme.dim)
    table.add_column("kind")
    table.add_column("text")
    table.add_column("status")

    corrections = list_corrections(root)
    rules = load_rules(paths.rules_path(root))
    linked = {rule.source_correction for rule in rules if rule.source_correction}

    for correction in corrections:
        status = "compiled" if correction.id in linked else "advisory (not enforced)"
        table.add_row(correction.id, "correction", correction.text, status)
    for rule in rules:
        status = f"enabled · {rule.severity}" if rule.enabled else "disabled"
        table.add_row(rule.id, "rule", rule.description, status)

    if not corrections and not rules:
        table.add_row("-", "-", "no corrections recorded", "-")
    return table
