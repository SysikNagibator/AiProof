"""Fast hook entrypoints for each agent event.

Contract: fail-open by default. An internal error must never brick the agent;
it is logged and a visible warning is surfaced in ``status``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from aiproof import gitutil, logging, paths
from aiproof.adapters.claude_code import ClaudeCodeAdapter
from aiproof.checks.base import CheckContext
from aiproof.claims.extractor import extract_claims
from aiproof.config import Settings, load_settings, merge_pinned, read_pinned
from aiproof.gate.gate import decide
from aiproof.guard import tamper_guard
from aiproof.ledger.store import LedgerStore

MAX_BLOCKS = 2
OUTPUT_LIMIT = 2000


def read_stdin() -> dict[str, Any]:
    """Read and parse the hook JSON payload from stdin (never raises)."""
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _emit(payload: dict[str, Any]) -> None:
    if payload:
        sys.stdout.write(json.dumps(payload))
        sys.stdout.flush()


def _effective(root: Path) -> Settings:
    settings = load_settings(root)
    return merge_pinned(settings, read_pinned(root))


def _previous_blocks(store: LedgerStore, session: str) -> int:
    count = 0
    for record in store.records(session=session):
        if record.get("event") != "gate_decision":
            continue
        payload = record.get("payload", {})
        if isinstance(payload, dict) and payload.get("block"):
            count += 1
    return count


def handle(event_name: str) -> int:
    """Dispatch a single hook event; returns the process exit code."""
    if paths.is_disabled():
        logging.log(f"disabled via AIPROOF_DISABLE; skipped {event_name}", level="warn")
        return 0

    adapter = ClaudeCodeAdapter()
    event = adapter.parse_event(read_stdin())
    root = paths.project_root(event.cwd)
    settings = _effective(root)
    store = LedgerStore(root)

    if event_name == "PreToolUse":
        reason = tamper_guard.guard_tool(event.tool_name, event.tool_input, settings)
        if reason:
            store.append(
                "tamper_attempt",
                {"tool": event.tool_name, "tool_input": event.tool_input, "reason": reason},
                session=event.session_id,
            )
            _emit(adapter.pretooluse_deny(reason)[1])
            return 0
        command = str(event.tool_input.get("command", "")) if event.tool_input else ""
        store.append(
            "tool_pre",
            {"tool": event.tool_name, "command": command},
            session=event.session_id,
        )
        return 0

    if event_name == "PostToolUse":
        command = str(event.tool_input.get("command", "")) if event.tool_input else ""
        output = str(event.raw.get("tool_response") or "")[:OUTPUT_LIMIT]
        store.append(
            "tool_post",
            {"tool": event.tool_name, "command": command, "output": output},
            session=event.session_id,
        )
        return 0

    if event_name == "SessionStart":
        start_commit = gitutil.head_commit(root) if gitutil.is_repo(root) else None
        ok, reason = __import__("aiproof.config", fromlist=["pinned_ok"]).pinned_ok(root)
        from aiproof.checks.config_integrity import protected_files

        snapshot = protected_files(root, settings.protected_paths)
        store.append(
            "session_start",
            {
                "cwd": str(root),
                "source": str(event.raw.get("source", "")),
                "start_commit": start_commit,
                "pinned_ok": ok,
                "pinned_reason": reason,
                "protected_files": snapshot,
            },
            session=event.session_id,
        )
        return 0

    if event_name == "Stop":
        return _handle_stop(adapter, store, root, settings, event)

    return 0


def _handle_stop(
    adapter: ClaudeCodeAdapter,
    store: LedgerStore,
    root: Path,
    settings: Any,
    event: Any,
) -> int:
    records = store.records(session=event.session_id)
    start_commit: str | None = None
    for record in records:
        if record.get("event") == "session_start":
            payload = record.get("payload", {})
            if isinstance(payload, dict):
                start_commit = payload.get("start_commit")

    message = event.last_message
    if not message:
        message = str(event.raw.get("transcript", ""))
    test_message = __import__("os").environ.get("AIPROOF_TEST_MESSAGE")
    if test_message:
        message = test_message

    claims = extract_claims(message)
    store.append(
        "claims_extracted",
        {"count": len(claims), "types": [str(c.type) for c in claims]},
        session=event.session_id,
    )

    blocks = _previous_blocks(store, event.session_id)
    capped = blocks >= MAX_BLOCKS

    ctx = CheckContext(
        root=root,
        settings=settings,
        session=event.session_id,
        start_commit=start_commit,
        records=records,
        claims=claims,
    )
    decision = decide(ctx, agent_lang=settings.agent_message_language, capped=capped)

    store.append(
        "check_result",
        {
            "results": [r.as_dict() for r in decision.results],
            "findings": [f.as_dict() for f in decision.findings],
        },
        session=event.session_id,
    )
    store.append("gate_decision", decision.as_dict(), session=event.session_id)

    if decision.block and decision.reason:
        _emit(adapter.stop_response(True, decision.reason)[1])
    return 0


def _safe_handle(event_name: str) -> int:
    try:
        return handle(event_name)
    except Exception as exc:
        logging.log(f"internal error in {event_name}: {exc!r}", level="error")
        return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: ``aiproof hook <Event>``."""
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: aiproof hook <EventName>", file=sys.stderr)
        return 2
    return _safe_handle(args[0])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
