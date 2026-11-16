"""Agent/IDE integration registry (single source of truth).

This module is *data*, not behaviour. Each adapter implementation must reference
an entry here by ``id``.

HONESTY RULES (see docs/THREAT_MODEL.md and the master spec §4/§15):
* ``status`` is ``verified`` ONLY when a human/agent has read the vendor's
  *current* documentation and recorded the date in ``verified``.
* Never invent config paths, hook event names or flags. If a detail is not yet
  confirmed, leave it empty and set ``status = UNVERIFIED`` with a note.
* ``support`` describes the *best realistic* integration tier we expect:
    - native-hooks : can observe lifecycle and BLOCK mid-session (Stop/PreToolUse)
    - mcp-only     : read-only self-check tools exposed over MCP; cannot block
    - wrapper      : post-hoc only, via ``aiproof run -- <agent cmd>``
    - rules-only   : no runtime integration; we only protect/redact its files
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# Date (ISO-8601) this project's docs were last consulted for Claude Code.
# Recorded when the Claude Code hooks reference + guide were read.
_CLAUDE_CODE_DOCS_READ = "2026-11-16"


class Kind(StrEnum):
    """How the agent is delivered to the user."""

    CLI = "cli"
    IDE = "ide"
    EXTENSION = "extension"
    TERMINAL = "terminal"
    CLOUD = "cloud"


class Support(StrEnum):
    """Integration tier."""

    NATIVE_HOOKS = "native-hooks"
    MCP_ONLY = "mcp-only"
    WRAPPER = "wrapper"
    RULES_ONLY = "rules-only"


class Status(StrEnum):
    """Verification status against *current* vendor docs."""

    VERIFIED = "verified"
    PLANNED = "planned"
    UNVERIFIED = "unverified"


@dataclass(frozen=True, slots=True)
class Agent:
    """A single AI coding agent / IDE integration target."""

    id: str
    name: str
    vendor: str
    kind: Kind
    support: Support
    status: Status
    verified: str | None = None
    notes: str = ""


# --------------------------------------------------------------------------- #
# Tier A: native lifecycle hooks (can block mid-session).
# --------------------------------------------------------------------------- #
_TIER_A: tuple[Agent, ...] = (
    Agent(
        "claude-code",
        "Claude Code",
        "Anthropic",
        Kind.CLI,
        Support.NATIVE_HOOKS,
        Status.VERIFIED,
        verified=_CLAUDE_CODE_DOCS_READ,
        notes="settings.json levels, PreToolUse/Stop JSON, stop_hook_active, exit codes.",
    ),
    Agent(
        "cursor",
        "Cursor",
        "Anysphere",
        Kind.IDE,
        Support.NATIVE_HOOKS,
        Status.PLANNED,
        notes="Cursor Hooks — verify event names and config file.",
    ),
    Agent(
        "kiro",
        "Kiro",
        "AWS",
        Kind.IDE,
        Support.NATIVE_HOOKS,
        Status.PLANNED,
        notes="Agent hooks / steering — verify.",
    ),
    Agent(
        "gemini-cli",
        "Gemini CLI",
        "Google",
        Kind.CLI,
        Support.NATIVE_HOOKS,
        Status.PLANNED,
        notes="settings.json extensions/hooks — verify event names.",
    ),
    Agent(
        "qwen-code",
        "Qwen Code",
        "Alibaba",
        Kind.CLI,
        Support.NATIVE_HOOKS,
        Status.PLANNED,
        notes="Gemini CLI fork — verify divergence.",
    ),
    Agent(
        "codex-cli",
        "Codex CLI",
        "OpenAI",
        Kind.CLI,
        Support.NATIVE_HOOKS,
        Status.UNVERIFIED,
        notes="Verify whether lifecycle hooks exist; else fall back to MCP/wrapper.",
    ),
    Agent(
        "opencode",
        "OpenCode",
        "SST",
        Kind.CLI,
        Support.NATIVE_HOOKS,
        Status.PLANNED,
        notes="Plugin/tool hooks (tool.execute.before/after) — verify.",
    ),
    Agent(
        "windsurf",
        "Windsurf",
        "Cognition",
        Kind.IDE,
        Support.NATIVE_HOOKS,
        Status.UNVERIFIED,
        notes="Cascade hooks — verify.",
    ),
    Agent(
        "junie",
        "Junie",
        "JetBrains",
        Kind.IDE,
        Support.NATIVE_HOOKS,
        Status.UNVERIFIED,
        notes="Verify hook support.",
    ),
    Agent(
        "copilot-cli",
        "GitHub Copilot CLI",
        "GitHub",
        Kind.CLI,
        Support.NATIVE_HOOKS,
        Status.UNVERIFIED,
        notes="Verify whether agent-mode hooks exist.",
    ),
    Agent(
        "goose",
        "Goose",
        "Block",
        Kind.CLI,
        Support.NATIVE_HOOKS,
        Status.UNVERIFIED,
        notes="Recipes/extensions; verify hooks.",
    ),
)

# --------------------------------------------------------------------------- #
# Tier B: MCP-only (read-only self-check tools; cannot block).
# --------------------------------------------------------------------------- #
_TIER_B: tuple[Agent, ...] = (
    Agent("cline", "Cline", "Cline", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED),
    Agent("roo-code", "Roo Code", "Roo", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED),
    Agent("kilo-code", "Kilo Code", "Kilo", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED),
    Agent("continue", "Continue", "Continue", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED),
    Agent("zed", "Zed", "Zed Industries", Kind.IDE, Support.MCP_ONLY, Status.PLANNED),
    Agent(
        "vscode-copilot",
        "GitHub Copilot (VS Code)",
        "GitHub",
        Kind.IDE,
        Support.MCP_ONLY,
        Status.PLANNED,
    ),
    Agent(
        "jetbrains-ai",
        "JetBrains AI Assistant",
        "JetBrains",
        Kind.IDE,
        Support.MCP_ONLY,
        Status.PLANNED,
    ),
    Agent("amazon-q", "Amazon Q Developer", "AWS", Kind.CLI, Support.MCP_ONLY, Status.PLANNED),
    Agent("augment", "Augment Code", "Augment", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED),
    Agent("warp", "Warp", "Warp", Kind.TERMINAL, Support.MCP_ONLY, Status.PLANNED),
    Agent("crush", "Crush", "Charm", Kind.CLI, Support.MCP_ONLY, Status.PLANNED),
    Agent("amp", "Amp", "Sourcegraph", Kind.CLI, Support.MCP_ONLY, Status.PLANNED),
    Agent("droid", "Droid", "Factory", Kind.CLI, Support.MCP_ONLY, Status.PLANNED),
    Agent("openhands", "OpenHands", "All Hands AI", Kind.CLI, Support.MCP_ONLY, Status.PLANNED),
    Agent("trae", "Trae", "ByteDance", Kind.IDE, Support.MCP_ONLY, Status.PLANNED),
    Agent("void", "Void", "Void", Kind.IDE, Support.MCP_ONLY, Status.PLANNED),
    Agent("tabnine", "Tabnine", "Tabnine", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED),
    Agent(
        "cody", "Sourcegraph Cody", "Sourcegraph", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED
    ),
    Agent(
        "firebender", "Firebender", "Firebender", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED
    ),
    Agent("codebuddy", "CodeBuddy", "Tencent", Kind.IDE, Support.MCP_ONLY, Status.PLANNED),
    Agent("qoder", "Qoder", "Alibaba", Kind.IDE, Support.MCP_ONLY, Status.PLANNED),
    Agent("iflow-cli", "iFlow CLI", "iFlow", Kind.CLI, Support.MCP_ONLY, Status.PLANNED),
    Agent("antigravity", "Antigravity", "Google", Kind.IDE, Support.MCP_ONLY, Status.PLANNED),
    Agent("rovodev", "Rovo Dev CLI", "Atlassian", Kind.CLI, Support.MCP_ONLY, Status.PLANNED),
    Agent("blackbox", "Blackbox AI", "Blackbox", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED),
    Agent("refact", "Refact.ai", "Refact", Kind.EXTENSION, Support.MCP_ONLY, Status.PLANNED),
    Agent("replit", "Replit Agent", "Replit", Kind.CLOUD, Support.MCP_ONLY, Status.PLANNED),
    Agent("devin", "Devin", "Cognition", Kind.CLOUD, Support.MCP_ONLY, Status.PLANNED),
    Agent("codex-cloud", "Codex (cloud)", "OpenAI", Kind.CLOUD, Support.MCP_ONLY, Status.PLANNED),
)

# --------------------------------------------------------------------------- #
# Tier C: wrapper mode (post-hoc verification of a finished process).
# --------------------------------------------------------------------------- #
_TIER_C: tuple[Agent, ...] = (
    Agent(
        "aider",
        "Aider",
        "Aider",
        Kind.CLI,
        Support.WRAPPER,
        Status.PLANNED,
        notes="No blocking hooks; verify MCP support before promoting.",
    ),
    Agent(
        "open-interpreter",
        "Open Interpreter",
        "Open Interpreter",
        Kind.CLI,
        Support.WRAPPER,
        Status.PLANNED,
    ),
    Agent("shell-gpt", "shell-gpt", "shell-gpt", Kind.CLI, Support.WRAPPER, Status.PLANNED),
    Agent("llm", "llm (simonw)", "Datasette", Kind.CLI, Support.WRAPPER, Status.PLANNED),
    Agent(
        "ollama",
        "Ollama",
        "Ollama",
        Kind.CLI,
        Support.WRAPPER,
        Status.PLANNED,
        notes="Local model runner; wrap whatever agent drives it.",
    ),
    Agent(
        "lm-studio",
        "LM Studio",
        "LM Studio",
        Kind.IDE,
        Support.WRAPPER,
        Status.PLANNED,
        notes="Local model server.",
    ),
    Agent("llama-cpp", "llama.cpp", "ggml", Kind.CLI, Support.WRAPPER, Status.PLANNED),
    Agent("vllm", "vLLM", "vLLM", Kind.CLI, Support.WRAPPER, Status.PLANNED),
    Agent(
        "generic-cli",
        "Any CLI agent",
        "-",
        Kind.CLI,
        Support.WRAPPER,
        Status.VERIFIED,
        verified=_CLAUDE_CODE_DOCS_READ,
        notes="aiproof run -- <cmd>: watch git before/after, verify claims post-hoc.",
    ),
)

# --------------------------------------------------------------------------- #
# Tier D: instruction/rules files we protect & redact (not agents themselves).
# --------------------------------------------------------------------------- #
INSTRUCTION_FILES: tuple[str, ...] = (
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".cursor/rules",
    ".github/copilot-instructions.md",
    ".windsurfrules",
    ".clinerules",
    ".roorules",
    ".rules",
    ".goosehints",
    "CONVENTIONS.md",
    ".aider.conf.yml",
    ".kiro/steering",
)

AGENTS: tuple[Agent, ...] = _TIER_A + _TIER_B + _TIER_C


def by_support(support: Support) -> tuple[Agent, ...]:
    """Return every agent in the given integration tier."""
    return tuple(a for a in AGENTS if a.support is support)


def verified_agents() -> tuple[Agent, ...]:
    """Return agents whose integration has been checked against current docs."""
    return tuple(a for a in AGENTS if a.status is Status.VERIFIED)


def get(agent_id: str) -> Agent:
    """Look up an agent by id; raises KeyError when unknown."""
    for agent in AGENTS:
        if agent.id == agent_id:
            return agent
    raise KeyError(agent_id)
