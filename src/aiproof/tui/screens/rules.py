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
    table.add_column(t("tui.id", lang), style=theme.dim)
    table.add_column(t("tui.kind", lang))
    table.add_column(t("tui.text", lang))
    table.add_column(t("tui.status", lang))

    corrections = list_corrections(root)
    rules = load_rules(paths.rules_path(root))
    linked = {rule.source_correction for rule in rules if rule.source_correction}

    for correction in corrections:
        status = t("tui.compiled", lang) if correction.id in linked else t("tui.advisory", lang)
        table.add_row(correction.id, t("tui.correction", lang), correction.text, status)
    for rule in rules:
        status = (
            f"{t('tui.enabled', lang)} · {rule.severity}"
            if rule.enabled
            else t("tui.disabled", lang)
        )
        table.add_row(rule.id, t("tui.rule", lang), rule.description, status)

    if not corrections and not rules:
        table.add_row("-", "-", t("tui.no_corrections", lang), "-")
    return table
