"""``aiproof mcp``: read-only stdio MCP server exposing self-check tools.

By design no tool can change pins, config or pause state.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from aiproof import __version__, paths
from aiproof.checks.base import CheckContext
from aiproof.claims.extractor import extract_claims
from aiproof.config import load_settings, merge_pinned, read_pinned
from aiproof.gate.gate import decide
from aiproof.ledger import verify

PROTOCOL_VERSION = "2024-11-05"

TOOLS: list[dict[str, Any]] = [
    {
        "name": "aiproof_status",
        "description": "Armed state, pinned-config integrity, ledger status.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "aiproof_verify_claims",
        "description": "Submit claims text; get per-claim verdicts (no side effects).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "cwd": {"type": "string"},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "aiproof_scan_secrets",
        "description": "Scan the git diff for secrets (returns types/locations only).",
        "inputSchema": {
            "type": "object",
            "properties": {"cwd": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "aiproof_receipt",
        "description": "Return the latest session receipt as JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {"cwd": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "aiproof_corrections_list",
        "description": "List corrections recorded for this project (advisory).",
        "inputSchema": {
            "type": "object",
            "properties": {"cwd": {"type": "string"}},
            "additionalProperties": False,
        },
    },
]


def _root_from(args: dict[str, Any]) -> Path:
    cwd = args.get("cwd")
    return paths.project_root(Path(str(cwd))) if cwd else paths.project_root()


def _result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        # ``ensure_ascii=True`` keeps a crafted lone surrogate inside a ledger
        # payload from making the stdio response unencodable.
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=True)}],
        "isError": False,
    }


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute a read-only tool and return an MCP tool result."""
    root = _root_from(args)
    if name == "aiproof_status":
        settings = merge_pinned(load_settings(root), read_pinned(root))
        return _result(
            {
                "ok": True,
                "project": str(root),
                "strictness": settings.strictness,
                "ledger": verify.verify(root).summary(),
            }
        )
    if name == "aiproof_verify_claims":
        settings = merge_pinned(load_settings(root), read_pinned(root))
        claims = extract_claims(str(args.get("text", "")))
        ctx = CheckContext(root=root, settings=settings, session="mcp", claims=claims)
        decision = decide(ctx, agent_lang=settings.agent_message_language, integrity=False)
        return _result(
            {
                "ok": True,
                "block": decision.block,
                "results": [r.as_dict() for r in decision.results],
                "findings": [f.as_dict() for f in decision.findings],
            }
        )
    if name == "aiproof_scan_secrets":
        from aiproof.redact.scanner import scan_diff

        findings = scan_diff(root)
        return _result({"ok": True, "findings": [f.as_dict() for f in findings]})
    if name == "aiproof_receipt":
        from aiproof.ledger.receipt import build_receipt
        from aiproof.ledger.store import LedgerStore

        session = LedgerStore(root).last_session()
        if session is None:
            return _result({"ok": False, "reason": "no sessions"})
        return _result({"ok": True, "receipt": build_receipt(root, session).as_dict()})
    if name == "aiproof_corrections_list":
        from aiproof.learn.corrections import list_corrections

        corrections = [c.as_dict() for c in list_corrections(root)]
        return _result({"ok": True, "corrections": corrections})
    return {
        "content": [{"type": "text", "text": json.dumps({"ok": False, "reason": "unknown tool"})}],
        "isError": True,
    }


def _handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    msg_id = message.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "aiproof", "version": __version__},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        raw_params = message.get("params", {})
        params = raw_params if isinstance(raw_params, dict) else {}
        name = str(params.get("name", ""))
        raw_args = params.get("arguments", {})
        args = raw_args if isinstance(raw_args, dict) else {}
        try:
            result = call_tool(name, args)
        except Exception as exc:  # never let one call kill the stdio loop
            result = {
                "content": [
                    {"type": "text", "text": json.dumps({"ok": False, "reason": str(exc)})}
                ],
                "isError": True,
            }
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if msg_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": "method not found"},
    }


def main() -> int:
    """Run the stdio MCP loop (one JSON-RPC message per line)."""
    for line in sys.stdin:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            message = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(message, dict):
            continue
        response = _handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
