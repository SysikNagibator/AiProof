"""Agent registry integrity."""

from __future__ import annotations

from aiproof.adapters import registry


def test_ids_unique() -> None:
    ids = [a.id for a in registry.AGENTS]
    assert len(ids) == len(set(ids))


def test_claude_code_verified() -> None:
    cc = registry.get("claude-code")
    assert cc.status is registry.Status.VERIFIED
    assert cc.verified is not None


def test_all_tiers_present() -> None:
    assert registry.by_support(registry.Support.NATIVE_HOOKS)
    assert registry.by_support(registry.Support.MCP_ONLY)
    assert registry.by_support(registry.Support.WRAPPER)


def test_instruction_files_are_paths() -> None:
    assert "CLAUDE.md" in registry.INSTRUCTION_FILES
    assert all(isinstance(p, str) for p in registry.INSTRUCTION_FILES)
