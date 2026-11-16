"""Declarative executable-rule DSL (stored as TOML).

Rules are deliberately small and deterministic. A rule can only inspect added
diff lines, the scope (path glob) and observed shell commands. Anything that
cannot be expressed here stays advisory in ``corrections.py``.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

try:  # optional writer, same policy as config.py
    import tomli_w
except ModuleNotFoundError:  # pragma: no cover - exercised only when extra missing
    tomli_w = None  # type: ignore[assignment]

SEVERITIES: tuple[str, ...] = ("block", "warn")
WAIVER_RE = re.compile(r"aiproof:(?:ignore|allow)", re.IGNORECASE)


class RuleError(ValueError):
    """Raised when a rule is malformed (bad severity, bad regex, bad glob)."""


@dataclass(slots=True)
class Rule:
    """One executable rule."""

    id: str
    description: str
    scope: str = "**/*"
    forbid_added_regex: tuple[str, ...] = ()
    require_added_regex: tuple[str, ...] = ()
    forbid_command_regex: tuple[str, ...] = ()
    severity: str = "warn"
    enabled: bool = False
    source_correction: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the TOML mapping for this rule."""
        data: dict[str, Any] = {
            "description": self.description,
            "scope": self.scope,
            "severity": self.severity,
            "enabled": self.enabled,
        }
        if self.forbid_added_regex:
            data["forbid_added_regex"] = list(self.forbid_added_regex)
        if self.require_added_regex:
            data["require_added_regex"] = list(self.require_added_regex)
        if self.forbid_command_regex:
            data["forbid_command_regex"] = list(self.forbid_command_regex)
        if self.source_correction:
            data["source_correction"] = self.source_correction
        return data

    @classmethod
    def from_dict(cls, rule_id: str, data: dict[str, Any]) -> Rule:
        """Build a rule from a raw TOML mapping."""
        description = str(data.get("description", "")).strip()
        if not description:
            raise RuleError(f"rule {rule_id!r} has no description")
        rule = cls(
            id=rule_id,
            description=description,
            scope=str(data.get("scope", "**/*")),
            forbid_added_regex=_str_tuple(data.get("forbid_added_regex")),
            require_added_regex=_str_tuple(data.get("require_added_regex")),
            forbid_command_regex=_str_tuple(data.get("forbid_command_regex")),
            severity=str(data.get("severity", "warn")),
            enabled=bool(data.get("enabled", False)),
            source_correction=str(data.get("source_correction", "")),
        )
        validate_rule(rule)
        return rule


@dataclass(frozen=True, slots=True)
class DiffFile:
    """A file with the lines it added relative to a baseline."""

    path: str
    added: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RuleHit:
    """A rule match with location and waiver state."""

    rule_id: str
    description: str
    severity: str
    path: str
    line: int
    text: str
    waiver: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe mapping."""
        return {
            "rule": self.rule_id,
            "description": self.description,
            "severity": self.severity,
            "path": self.path,
            "line": self.line,
            "text": self.text,
            "waiver": self.waiver,
        }


def _str_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return ()


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a git-style glob (``**``, ``*``, ``?``) to a regex."""
    text = pattern.replace("\\", "/").strip()
    out: list[str] = ["^"]
    index = 0
    while index < len(text):
        char = text[index]
        if char == "*":
            if index + 1 < len(text) and text[index + 1] == "*":
                if index + 2 < len(text) and text[index + 2] == "/":
                    out.append("(?:.*/)?")
                    index += 3
                    continue
                out.append(".*")
                index += 2
                continue
            out.append("[^/]*")
            index += 1
            continue
        if char == "?":
            out.append("[^/]")
        elif char in ".+()|[]{}^$\\":
            out.append("\\" + char)
        else:
            out.append(char)
        index += 1
    out.append("$")
    try:
        return re.compile("".join(out))
    except re.error as exc:  # pragma: no cover - defensive
        raise RuleError(f"invalid scope glob {pattern!r}: {exc}") from exc


def matches_scope(scope: str, path: str) -> bool:
    """Return True when *path* is inside *scope*."""
    return bool(glob_to_regex(scope).match(path.replace("\\", "/")))


def validate_rule(rule: Rule) -> None:
    """Raise :class:`RuleError` when a rule cannot be evaluated safely."""
    if not rule.id.strip():
        raise RuleError("rule id is empty")
    if rule.severity not in SEVERITIES:
        raise RuleError(f"rule {rule.id!r}: severity must be one of {SEVERITIES}")
    glob_to_regex(rule.scope)
    for pattern in (*rule.forbid_added_regex, *rule.require_added_regex):
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise RuleError(f"rule {rule.id!r}: invalid regex {pattern!r}: {exc}") from exc
    for pattern in rule.forbid_command_regex:
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise RuleError(f"rule {rule.id!r}: invalid command regex {pattern!r}: {exc}") from exc


def apply_rule(
    rule: Rule,
    files: list[DiffFile] | tuple[DiffFile, ...],
    commands: list[str] | tuple[str, ...] = (),
    *,
    include_waivers: bool = False,
) -> list[RuleHit]:
    """Evaluate one rule against a diff and observed commands."""
    validate_rule(rule)
    hits: list[RuleHit] = []
    forbid = tuple(re.compile(p, re.IGNORECASE) for p in rule.forbid_added_regex)
    require = tuple(re.compile(p, re.IGNORECASE) for p in rule.require_added_regex)
    command_patterns = tuple(re.compile(p, re.IGNORECASE) for p in rule.forbid_command_regex)

    for file in files:
        if not matches_scope(rule.scope, file.path):
            continue
        if forbid:
            for number, line in enumerate(file.added, start=1):
                if not any(pattern.search(line) for pattern in forbid):
                    continue
                waived = bool(WAIVER_RE.search(line))
                if waived and not include_waivers:
                    continue
                hits.append(
                    RuleHit(
                        rule.id,
                        rule.description,
                        rule.severity,
                        file.path,
                        number,
                        line.strip()[:160],
                        waived,
                    )
                )
        if (
            require
            and file.added
            and not any(pattern.search(line) for line in file.added for pattern in require)
        ):
            hits.append(
                RuleHit(
                    rule.id,
                    rule.description,
                    rule.severity,
                    file.path,
                    0,
                    "(missing required pattern)",
                )
            )

    for command in commands:
        for pattern in command_patterns:
            if pattern.search(command):
                hits.append(
                    RuleHit(
                        rule.id,
                        rule.description,
                        rule.severity,
                        "<command>",
                        0,
                        command.strip()[:160],
                    )
                )
                break
    return hits


def apply_rules(
    rules: list[Rule] | tuple[Rule, ...],
    files: list[DiffFile] | tuple[DiffFile, ...],
    commands: list[str] | tuple[str, ...] = (),
) -> list[RuleHit]:
    """Evaluate every *enabled* rule."""
    hits: list[RuleHit] = []
    for rule in rules:
        if rule.enabled:
            hits.extend(apply_rule(rule, files, commands))
    return hits


def load_rules(path: Path) -> list[Rule]:
    """Load rules from a TOML file (missing/invalid file -> empty list)."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return []
    table = raw.get("rule")
    if not isinstance(table, dict):
        return []
    rules: list[Rule] = []
    for rule_id, data in table.items():
        if not isinstance(data, dict):
            continue
        try:
            rules.append(Rule.from_dict(str(rule_id), data))
        except RuleError:
            continue
    return rules


def save_rules(path: Path, rules: list[Rule] | tuple[Rule, ...]) -> None:
    """Atomically write rules to *path* (TOML)."""
    if tomli_w is None:  # pragma: no cover
        raise RuntimeError("tomli-w is required to save rules")
    payload: dict[str, Any] = {"rule": {rule.id: rule.to_dict() for rule in rules}}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(tomli_w.dumps(payload).encode("utf-8"))
    tmp.replace(path)


def upsert_rule(rules: list[Rule], rule: Rule) -> list[Rule]:
    """Return *rules* with *rule* inserted or replaced (by id)."""
    out = [existing for existing in rules if existing.id != rule.id]
    out.append(rule)
    out.sort(key=lambda item: item.id)
    return out


def set_enabled(rules: list[Rule], rule_id: str, enabled: bool) -> list[Rule]:
    """Return *rules* with one rule toggled; raises ``KeyError`` when absent."""
    if not any(rule.id == rule_id for rule in rules):
        raise KeyError(rule_id)
    return [replace(rule, enabled=enabled) if rule.id == rule_id else rule for rule in rules]


__all__ = [
    "SEVERITIES",
    "DiffFile",
    "Rule",
    "RuleError",
    "RuleHit",
    "apply_rule",
    "apply_rules",
    "glob_to_regex",
    "load_rules",
    "matches_scope",
    "save_rules",
    "set_enabled",
    "upsert_rule",
    "validate_rule",
]
