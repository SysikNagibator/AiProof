"""Adapter interface shared by every agent integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class SupportLevel(StrEnum):
    """How deeply an adapter can integrate with an agent."""

    NATIVE_HOOKS = "native-hooks"
    MCP_ONLY = "mcp-only"
    WRAPPER = "wrapper"


@dataclass(slots=True)
class Event:
    """A normalized hook/agent event."""

    name: str
    session_id: str
    cwd: Path
    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    prompt: str = ""
    last_message: str = ""
    stop_hook_active: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InstallResult:
    """Result of an install/uninstall action."""

    changed: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


class Adapter(ABC):
    """Base class for agent adapters."""

    id: str = "base"
    support: SupportLevel = SupportLevel.MCP_ONLY

    @abstractmethod
    def detect(self, root: Path) -> bool:
        """Return True when this agent appears to be in use for *root*."""

    @abstractmethod
    def install(self, root: Path, *, dry_run: bool = False) -> InstallResult:
        """Install the integration (idempotent), backing up touched files."""

    @abstractmethod
    def uninstall(self, root: Path, *, dry_run: bool = False) -> InstallResult:
        """Remove only AiProof's own entries."""

    @abstractmethod
    def parse_event(self, raw: dict[str, Any]) -> Event:
        """Normalize a raw stdin JSON payload into an :class:`Event`."""

    def respond(self, block: bool, reason: str) -> tuple[int, dict[str, Any]]:
        """Return ``(exit_code, json_output)`` for a decision."""
        return 0, {}
