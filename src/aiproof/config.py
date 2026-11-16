"""Layered configuration and the *pinned* gate configuration.

Layers (low -> high): built-in defaults, user config, project config
(advisory), ``AIPROOF_*`` environment, CLI flags.

Gate-critical keys are read ONLY from the pinned copy (``pinned.toml``) so the
agent can never relax them by editing an in-repo file.
"""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from aiproof import paths

try:  # optional writer
    import tomli_w
except ModuleNotFoundError:  # pragma: no cover - exercised only when extra missing
    tomli_w = None  # type: ignore[assignment]

STRICTNESS_PRESETS: tuple[str, ...] = ("observe", "warn", "enforce", "strict")
ERROR_POLICIES: tuple[str, ...] = ("open", "closed")
THEMES: tuple[str, ...] = ("green", "mono", "amber")

DEFAULT_CHECKS: tuple[str, ...] = (
    "commit_exists",
    "file_changed",
    "tests_ran",
    "test_tamper",
    "secrets_in_diff",
    "todo_integrity",
    "config_integrity",
    "learn_rules",
)

DEFAULT_PROTECTED: tuple[str, ...] = (
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".mcp.json",
    "**/mcp.json",
    ".aiproof/**",
    "{data}/**",
    ".git/hooks/**",
)

# Keys the gate trusts only from the pinned copy.
CRITICAL_KEYS: frozenset[str] = frozenset(
    {
        "strictness",
        "test_command",
        "enabled_checks",
        "protected_paths",
        "protect_ci",
    }
)


@dataclass(slots=True)
class Settings:
    """Effective configuration for a project."""

    strictness: str = "enforce"
    on_internal_error: str = "open"
    language: str = "auto"
    theme: str = "green"
    ascii_only: bool = False
    animations: bool = True
    test_command: str | None = None
    protect_ci: bool = False
    agent_message_language: str = "en"
    enabled_checks: tuple[str, ...] = DEFAULT_CHECKS
    protected_paths: tuple[str, ...] = DEFAULT_PROTECTED
    allowlist_paths: tuple[str, ...] = ()
    allowlist_regexes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/TOML-serializable mapping (``None`` values dropped)."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def with_critical(self) -> Settings:
        """Return a copy keeping only gate-critical keys (others reset to default)."""
        base = Settings()
        for key in CRITICAL_KEYS:
            setattr(base, key, getattr(self, key))
        return base


def _coerce(value: object, default: object) -> object:
    """Best-effort TOML value coercion, ignoring obviously wrong types."""
    if isinstance(default, bool):
        return bool(value)
    if isinstance(default, int) and not isinstance(value, bool):
        return int(value) if isinstance(value, int) else default
    if isinstance(default, str):
        return value if isinstance(value, str) else default
    if isinstance(default, tuple):
        if isinstance(value, (list, tuple)):
            return tuple(str(v) for v in value)
        return default
    return value


def _apply(data: dict[str, Any], base: Settings) -> Settings:
    """Apply a raw TOML mapping onto a Settings instance."""
    for key, value in data.items():
        if not hasattr(base, key):
            continue
        setattr(base, key, _coerce(value, getattr(base, key)))
    return base


def _read_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file, returning ``{}`` when missing or invalid."""
    try:
        raw = path.read_bytes()
    except OSError:
        return {}
    try:
        parsed = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return {}
    return parsed


_ENV_MAP: dict[str, str] = {
    "AIPROOF_STRICTNESS": "strictness",
    "AIPROOF_ON_INTERNAL_ERROR": "on_internal_error",
    "AIPROOF_LANG": "language",
    "AIPROOF_THEME": "theme",
    "AIPROOF_TEST_COMMAND": "test_command",
    "AIPROOF_AGENT_MESSAGE_LANGUAGE": "agent_message_language",
    "AIPROOF_PROTECT_CI": "protect_ci",
}


def _apply_env(base: Settings) -> Settings:
    """Apply ``AIPROOF_*`` environment overrides."""
    for env_key, attr in _ENV_MAP.items():
        raw = os.environ.get(env_key)
        if raw is None:
            continue
        default = getattr(base, attr)
        if attr == "protect_ci":
            setattr(base, attr, raw.strip() in {"1", "true", "yes", "on"})
        else:
            setattr(base, attr, _coerce(raw, default))
    return base


def load_settings(
    root: Path | None = None, cli_overrides: dict[str, Any] | None = None
) -> Settings:
    """Load the effective settings for *root* following the layer order."""
    settings = Settings()
    _apply(_read_toml(paths.global_config_path()), settings)
    if root is not None:
        _apply(_read_toml(paths.repo_config_path(root)), settings)
    _apply_env(settings)
    if cli_overrides:
        _apply(cli_overrides, settings)
    return settings


# --------------------------------------------------------------------------- #
# Pinned configuration
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class Pinned:
    """A pinned, gate-authoritative snapshot plus its self-hash."""

    settings: Settings
    sha256: str

    def as_record(self) -> dict[str, Any]:
        """Return the on-disk record for ``pinned.toml``."""
        return {"sha256": self.sha256, "settings": self.settings.to_dict()}


def _canonical_settings(settings: Settings) -> str:
    """Return a stable canonical JSON encoding of the critical settings."""
    critical = settings.with_critical().to_dict()
    return json.dumps(critical, sort_keys=True, separators=(",", ":"))


def pin_digest(settings: Settings) -> str:
    """Compute the SHA-256 over the canonical critical settings."""
    return hashlib.sha256(_canonical_settings(settings).encode("utf-8")).hexdigest()


def read_pinned(root: Path) -> Pinned | None:
    """Read and verify the pinned settings; returns ``None`` when absent."""
    data = _read_toml(paths.pinned_path(root))
    raw_settings = data.get("settings")
    sha = data.get("sha256")
    if not isinstance(raw_settings, dict) or not isinstance(sha, str):
        return None
    settings = _apply(raw_settings, Settings())
    return Pinned(settings=settings, sha256=sha)


def write_pinned(root: Path, settings: Settings) -> Pinned:
    """Write the pinned settings (gitignore the project dir) and return them."""
    if tomli_w is None:  # pragma: no cover
        raise RuntimeError("tomli-w is required to write pinned settings")
    target = paths.pinned_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = pin_digest(settings)
    record = Pinned(settings=settings, sha256=digest).as_record()
    target.write_bytes(tomli_w.dumps(record).encode("utf-8"))
    return Pinned(settings=settings, sha256=digest)


def pinned_ok(root: Path) -> tuple[bool, str]:
    """Return ``(ok, reason)`` describing pinned-config integrity."""
    pinned = read_pinned(root)
    if pinned is None:
        return False, "pinned settings missing; run `aiproof init`"
    if pin_digest(pinned.settings) != pinned.sha256:
        return False, "pinned settings hash mismatch (tampered)"
    return True, "ok"


def merge_pinned(base: Settings, pinned: Pinned | None) -> Settings:
    """Overlay pinned critical keys on top of the effective settings."""
    if pinned is None:
        return replace(base)
    for key in CRITICAL_KEYS:
        setattr(base, key, getattr(pinned.settings, key))
    return base
