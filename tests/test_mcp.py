"""MCP server: read-only tools and JSON-RPC framing."""

from __future__ import annotations

import json
from pathlib import Path

from aiproof.mcp.server import TOOLS, _handle, call_tool


def _text(result: dict) -> dict:
    return json.loads(result["content"][0]["text"])


def test_tools_are_read_only() -> None:
    names = {t["name"] for t in TOOLS}
    assert "aiproof_status" in names
    assert not any(n.startswith(("aiproof_pause", "aiproof_set", "aiproof_pin")) for n in names)


def test_status_tool(tmp_path: Path) -> None:
    payload = _text(call_tool("aiproof_status", {"cwd": str(tmp_path)}))
    assert payload["ok"] is True
    assert "strictness" in payload


def test_verify_claims_tool_blocks(tmp_path: Path) -> None:
    payload = _text(
        call_tool("aiproof_verify_claims", {"cwd": str(tmp_path), "text": "all tests pass"})
    )
    assert payload["ok"] is True
    assert payload["block"] is True


def test_scan_secrets_tool_empty(tmp_path: Path) -> None:
    payload = _text(call_tool("aiproof_scan_secrets", {"cwd": str(tmp_path)}))
    assert payload["findings"] == []


def test_unknown_tool_is_error() -> None:
    result = call_tool("nope", {})
    assert result["isError"] is True


def test_receipt_tool_is_json_serializable(tmp_path: Path) -> None:
    """Regression: the receipt tool used to return a non-serializable dataclass."""
    from aiproof.ledger.store import LedgerStore

    store = LedgerStore(tmp_path)
    store.append("session_start", {"cwd": str(tmp_path)}, session="s1")
    payload = _text(call_tool("aiproof_receipt", {"cwd": str(tmp_path)}))
    assert payload["ok"] is True
    assert payload["receipt"]["session"] == "s1"


def test_receipt_tool_without_sessions(tmp_path: Path) -> None:
    payload = _text(call_tool("aiproof_receipt", {"cwd": str(tmp_path)}))
    assert payload["ok"] is False


def test_corrections_tool_lists_recorded(tmp_path: Path) -> None:
    from aiproof.learn.corrections import record_correction

    record_correction(tmp_path, "always run the tests")
    payload = _text(call_tool("aiproof_corrections_list", {"cwd": str(tmp_path)}))
    assert payload["ok"] is True
    assert any(c["text"] == "always run the tests" for c in payload["corrections"])


def test_tool_call_never_kills_the_loop(monkeypatch) -> None:
    """A raising tool must surface as isError, not break the JSON-RPC loop."""
    import aiproof.mcp.server as server

    def boom(_name: str, _args: dict) -> dict:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(server, "call_tool", boom)
    response = server._handle(
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "x"}}
    )
    assert response is not None
    assert response["result"]["isError"] is True


def test_initialize_handshake() -> None:
    response = _handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert response is not None
    assert response["result"]["serverInfo"]["name"] == "aiproof"


def test_tools_list() -> None:
    response = _handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert response is not None
    assert len(response["result"]["tools"]) == len(TOOLS)


def test_notification_returns_none() -> None:
    assert _handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_unknown_method_errors() -> None:
    response = _handle({"jsonrpc": "2.0", "id": 9, "method": "bogus"})
    assert response is not None and "error" in response
