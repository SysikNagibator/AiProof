"""Compile natural-language corrections into executable rules where possible.

This is intentionally conservative: only a small set of unambiguous templates is
compiled. Everything else is returned as an *advisory* candidate and is never
enforced. A compiled rule starts disabled until a human enables it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from aiproof.learn.corrections import Correction, list_corrections
from aiproof.learn.dsl import Rule

_IMPORT_RE = re.compile(
    r"(?i)(?:never|do not|don't|не)\s+(?:import|импортир\w*|импортируй)\s+"
    r"[`\"']?([A-Za-z_][\w.]*)[`\"']?\s+(?:in|inside|в|во)\s+([\w./*_-]+)"
)
_COMMAND_RE = re.compile(
    r"(?i)(?:never|do not|don't|не)\s+"
    r"(?:run|launch|execute|запускай|запускать|выполняй)\s+[`\"']([^`\"']+)[`\"']"
)
_PATH_RE = re.compile(
    r"(?i)(?:never|do not|don't|не)\s+"
    r"(?:edit|touch|change|modify|commit|редактир\w*|трогай|меняй|коммить)\s+"
    r"[`\"']?([\w.*-]*[/.][\w./*_-]+)"
)


@dataclass(frozen=True, slots=True)
class Candidate:
    """A correction and the rule it compiled to, when any."""

    correction_id: str
    correction_text: str
    rule: Rule | None
    reason: str

    @property
    def compiled(self) -> bool:
        """Return True when an executable rule was produced."""
        return self.rule is not None

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe mapping."""
        return {
            "correction": self.correction_id,
            "text": self.correction_text,
            "compiled": self.compiled,
            "reason": self.reason,
            "rule": self.rule.to_dict() | {"id": self.rule.id} if self.rule else None,
        }


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned[:40] or "rule"


def _candidate_import(correction: Correction) -> Candidate | None:
    match = _IMPORT_RE.search(correction.text)
    if not match:
        return None
    module, scope = match.group(1), match.group(2)
    rule = Rule(
        id=f"no-import-{_slug(module)}-{_slug(scope)}",
        description=f"Do not import {module} in {scope}",
        scope=scope,
        # ``import os, django`` must be caught too, not only a line that starts
        # with the module name.
        forbid_added_regex=(
            rf"(?i)^\s*from\s+{re.escape(module)}\b"
            rf"|^\s*import\s+[^\n]*\b{re.escape(module)}\b",
        ),
        severity="block",
        enabled=False,
        source_correction=correction.id,
    )
    return Candidate(correction.id, correction.text, rule, "import rule compiled")


def _candidate_command(correction: Correction) -> Candidate | None:
    match = _COMMAND_RE.search(correction.text)
    if not match:
        return None
    command = match.group(1).strip()
    rule = Rule(
        id=f"no-command-{_slug(command)}",
        description=f"Do not run `{command}`",
        # Word/hyphen boundaries so ``git push --force`` does not also block
        # ``git push --force-with-lease``.
        forbid_command_regex=(rf"(?<![\w-]){re.escape(command)}(?![\w-])",),
        severity="block",
        enabled=False,
        source_correction=correction.id,
    )
    return Candidate(correction.id, correction.text, rule, "command rule compiled")


def _candidate_path(correction: Correction) -> Candidate | None:
    match = _PATH_RE.search(correction.text)
    if not match:
        return None
    path = match.group(1).strip().rstrip("/")
    rule = Rule(
        id=f"no-edit-{_slug(path)}",
        description=f"Do not edit {path}",
        scope=path,
        forbid_added_regex=(r".",),
        severity="block",
        enabled=False,
        source_correction=correction.id,
    )
    return Candidate(correction.id, correction.text, rule, "path-lock rule compiled")


def _candidate_db_mock(correction: Correction) -> Candidate | None:
    lowered = correction.text.casefold()
    if "mock" not in lowered:
        return None
    targets = ("db", "database", "session", "engine")
    scopes = ("integration", "интеграц")
    if not any(target in lowered for target in targets):
        return None
    if not any(scope in lowered for scope in scopes):
        return None
    rule = Rule(
        id="no-db-mock-in-integration",
        description="Do not mock the database in integration tests",
        scope="tests/integration/**/*.py",
        forbid_added_regex=(r"(?i)\bmock\.patch\(.*(?:db|session|engine)",),
        severity="block",
        enabled=False,
        source_correction=correction.id,
    )
    return Candidate(correction.id, correction.text, rule, "integration-db-mock rule compiled")


_TEMPLATES = (
    _candidate_db_mock,
    _candidate_import,
    _candidate_command,
    _candidate_path,
)


def compile_correction(correction: Correction) -> Candidate:
    """Compile one correction, or return an advisory candidate."""
    for template in _TEMPLATES:
        candidate = template(correction)
        if candidate is not None:
            return candidate
    return Candidate(
        correction.id,
        correction.text,
        None,
        "no executable template matched; stays advisory (never enforced)",
    )


def compile_all(root: Path, existing: list[Rule] | None = None) -> list[Candidate]:
    """Compile every correction that is not already linked to a rule."""
    linked = {rule.source_correction for rule in (existing or []) if rule.source_correction}
    return [
        compile_correction(correction)
        for correction in list_corrections(root)
        if correction.id not in linked
    ]


__all__ = ["Candidate", "compile_all", "compile_correction"]
