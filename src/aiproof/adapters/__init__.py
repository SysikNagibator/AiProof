"""Adapter registry: instances and detection helpers."""

from __future__ import annotations

from pathlib import Path

from aiproof.adapters.base import Adapter
from aiproof.adapters.claude_code import ClaudeCodeAdapter
from aiproof.adapters.generic_mcp import McpAdapter
from aiproof.adapters.registry import AGENTS, Agent, Kind, Status, Support, by_support, get

ADAPTERS: tuple[Adapter, ...] = (ClaudeCodeAdapter(), McpAdapter())


def adapter(agent_id: str) -> Adapter | None:
    """Return the adapter instance for an agent id, if implemented."""
    for candidate in ADAPTERS:
        if candidate.id == agent_id:
            return candidate
    return None


def detect_all(root: Path) -> list[Adapter]:
    """Return every implemented adapter that detects its agent in *root*."""
    return [a for a in ADAPTERS if a.detect(root)]


__all__ = [
    "ADAPTERS",
    "AGENTS",
    "Agent",
    "Kind",
    "Status",
    "Support",
    "adapter",
    "by_support",
    "detect_all",
    "get",
]
