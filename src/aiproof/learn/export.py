"""Export enabled rules into a marker block inside ``AGENTS.md``.

User text outside the markers is never modified. The block lists only enabled
rules and their one-line descriptions, so it cannot leak secrets (corrections are
redacted by the ledger before they ever reach this point).
"""

from __future__ import annotations

import os
from pathlib import Path

from aiproof.i18n import t
from aiproof.learn.dsl import Rule

MARKER_START = "<!-- aiproof:start -->"
MARKER_END = "<!-- aiproof:end -->"


def render_block(rules: list[Rule] | tuple[Rule, ...], lang: str = "en") -> str:
    """Render the marker block for the *enabled* rules."""
    enabled = [rule for rule in rules if rule.enabled]
    lines: list[str] = [
        MARKER_START,
        f"## {t('learn.agents_md_title', lang)}",
        "",
        t("learn.agents_md_intro", lang),
        "",
    ]
    if enabled:
        for rule in sorted(enabled, key=lambda item: item.id):
            lines.append(f"- **{rule.id}** ({rule.severity}) — {rule.description}")
            lines.append(f"  - scope: `{rule.scope}`")
    else:
        lines.append(t("learn.agents_md_none", lang))
    lines += ["", f"_{t('learn.agents_md_footer', lang)}_", MARKER_END]
    return "\n".join(lines)


def upsert_block(existing: str, block: str) -> str:
    """Replace the marker block in *existing*, or append it when absent."""
    start = existing.find(MARKER_START)
    end = existing.find(MARKER_END)
    if start != -1 and end != -1 and end > start:
        return existing[:start] + block + existing[end + len(MARKER_END) :]
    if not existing.strip():
        return block + "\n"
    return existing.rstrip() + "\n\n" + block + "\n"


def write_export(
    root: Path, rules: list[Rule] | tuple[Rule, ...], *, target: str = "AGENTS.md", lang: str = "en"
) -> tuple[Path, bool]:
    """Write the export block; returns ``(path, changed)``."""
    path = root / target
    original = path.read_text(encoding="utf-8") if path.is_file() else ""
    updated = upsert_block(original, render_block(rules, lang))
    if updated == original:
        return path, False
    if path.is_file():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(original, encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(updated, encoding="utf-8")
    os.replace(tmp, path)
    return path, True


__all__ = ["MARKER_END", "MARKER_START", "render_block", "upsert_block", "write_export"]
