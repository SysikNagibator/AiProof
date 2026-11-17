"""Redaction with stable, non-reversible placeholders."""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aiproof.redact import entropy
from aiproof.redact.patterns import ENTROPY_CANDIDATE, SECRET_PATTERNS, SENSITIVE_HINT, Pattern

PLACEHOLDER_RE = re.compile(r"\[REDACTED:[a-z_]+:[0-9a-f]{8}\]")


def fingerprint(secret: str) -> str:
    """Return an 8-hex, non-reversible fingerprint for a secret value."""
    # ``surrogatepass`` avoids UnicodeEncodeError on lone surrogates that can arrive
    # from JSON escapes or damaged files.
    digest = hashlib.sha256(secret.encode("utf-8", "surrogatepass")).hexdigest()
    return digest[:8]


def placeholder(type_: str, secret: str) -> str:
    """Return the stable placeholder for a secret of a given type."""
    return f"[REDACTED:{type_}:{fingerprint(secret)}]"


@dataclass(slots=True)
class Finding:
    """A detected secret, without the secret value."""

    type: str
    fingerprint: str
    start: int = 0
    end: int = 0
    entropy: bool = False


@dataclass(slots=True)
class Allowlist:
    """Paths/regexes/fingerprints that must never be reported or redacted."""

    paths: tuple[str, ...] = ()
    regexes: tuple[str, ...] = ()
    fingerprints: tuple[str, ...] = ()
    _compiled: list[re.Pattern[str]] = field(default_factory=list, repr=False)

    def compile(self) -> None:
        """Pre-compile the regex allowlist."""
        self._compiled = [re.compile(rx) for rx in self.regexes]

    def allows(self, secret: str, fp: str) -> bool:
        """Return True when *secret* is explicitly allowed."""
        if fp in self.fingerprints:
            return True
        return any(rx.search(secret) for rx in self._compiled)

    def allows_path(self, location: str) -> bool:
        """Return True when *location* matches a path allowlist entry."""
        from fnmatch import fnmatch

        normalised = location.replace("\\", "/")
        for entry in self.paths:
            pattern = entry.replace("\\", "/").rstrip("/")
            if fnmatch(normalised, pattern) or normalised.startswith(pattern + "/"):
                return True
        return False


def load_allowlist(path: Path) -> Allowlist:
    """Load an allowlist from a TOML file (returns empty on missing/invalid)."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return Allowlist()
    return Allowlist(
        paths=tuple(str(p) for p in raw.get("paths", [])),
        regexes=tuple(str(r) for r in raw.get("regexes", [])),
        fingerprints=tuple(str(f) for f in raw.get("fingerprints", [])),
    )


def _sub_pattern(text: str, pattern: Pattern, allowlist: Allowlist) -> str:
    def repl(match: re.Match[str]) -> str:
        secret = match.group(pattern.group)
        if secret is None or PLACEHOLDER_RE.fullmatch(secret.strip()):
            return match.group(0)
        fp = fingerprint(secret)
        if allowlist.allows(secret, fp):
            return match.group(0)
        if pattern.group == 0:
            return placeholder(pattern.type, secret)
        return (
            match.string[match.start() : match.start(pattern.group)]
            + placeholder(pattern.type, secret)
            + match.string[match.end(pattern.group) : match.end()]
        )

    return pattern.regex.sub(repl, text)


def _redact_entropy(text: str, allowlist: Allowlist) -> str:
    out_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        if not SENSITIVE_HINT.search(line):
            out_lines.append(line)
            continue

        def repl(match: re.Match[str]) -> str:
            token = match.group(0)
            if PLACEHOLDER_RE.search(token):
                return token
            if not entropy.looks_secret(token):
                return token
            fp = fingerprint(token)
            if allowlist.allows(token, fp):
                return token
            return placeholder("entropy", token)

        out_lines.append(ENTROPY_CANDIDATE.sub(repl, line))
    return "".join(out_lines)


def redact_text(text: str, allowlist: Allowlist | None = None) -> str:
    """Redact every known/entropy-detected secret in *text* (idempotent)."""
    allow = allowlist or Allowlist()
    if not allow._compiled:
        allow.compile()
    result = text
    for pattern in SECRET_PATTERNS:
        result = _sub_pattern(result, pattern, allow)
    return _redact_entropy(result, allow)


def find_secrets(text: str, allowlist: Allowlist | None = None) -> list[Finding]:
    """Return findings (type + fingerprint + span) without any secret value.

    The same token can match several patterns (e.g. an OpenAI key also matches
    ``assigned_secret`` and the entropy pass); only the first finding per
    ``(fingerprint, start, end)`` is kept.
    """
    allow = allowlist or Allowlist()
    if not allow._compiled:
        allow.compile()
    findings: list[Finding] = []
    seen: set[tuple[str, int, int]] = set()

    def add(finding: Finding) -> None:
        key = (finding.fingerprint, finding.start, finding.end)
        if key in seen:
            return
        seen.add(key)
        findings.append(finding)

    for pattern in SECRET_PATTERNS:
        for match in pattern.regex.finditer(text):
            secret = match.group(pattern.group)
            if secret is None:
                continue
            fp = fingerprint(secret)
            if allow.allows(secret, fp):
                continue
            add(Finding(pattern.type, fp, match.start(pattern.group), match.end(pattern.group)))
    for line_match in re.finditer(r"[^\r\n]+", text):
        line = line_match.group(0)
        if not SENSITIVE_HINT.search(line):
            continue
        for candidate in ENTROPY_CANDIDATE.finditer(line):
            token = candidate.group(0)
            if not entropy.looks_secret(token):
                continue
            fp = fingerprint(token)
            if allow.allows(token, fp):
                continue
            start = line_match.start() + candidate.start()
            add(Finding("entropy", fp, start, start + len(token), entropy=True))
    return findings


def redact_json(obj: Any, allowlist: Allowlist | None = None) -> Any:
    """Recursively redact every string (keys included) inside a JSON-like structure."""
    if isinstance(obj, str):
        return redact_text(obj, allowlist)
    if isinstance(obj, dict):
        return {redact_text(str(k), allowlist): redact_json(v, allowlist) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_json(v, allowlist) for v in obj]
    return obj
