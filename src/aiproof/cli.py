"""``aiproof`` command-line entrypoint (non-interactive parity for the TUI)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from aiproof import __author__, __version__, paths, version_string
from aiproof.adapters import AGENTS, by_support
from aiproof.adapters.registry import Status, Support
from aiproof.bench.runner import run_scenarios
from aiproof.checks.base import CheckContext
from aiproof.claims.extractor import extract_claims
from aiproof.config import STRICTNESS_PRESETS, THEMES, load_settings, merge_pinned, read_pinned
from aiproof.gate.gate import decide
from aiproof.guard.pin import HumanOnlyError
from aiproof.i18n import KNOWN_LANGS, available, detect_language, is_reviewed, t
from aiproof.ledger import verify
from aiproof.ledger.receipt import build_receipt, render_html, render_json, render_md
from aiproof.ledger.store import LedgerStore
from aiproof.maintenance import doctor, install, pause
from aiproof.redact.redactor import Allowlist, load_allowlist
from aiproof.redact.scanner import (
    scan_agent_histories,
    scan_diff,
    scan_instruction_files,
    scan_tree,
)


def _emit(text: str) -> None:
    sys.stdout.write(text + "\n")


def _json(data: object) -> None:
    _emit(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _say(key: str, **vars_: object) -> None:
    """Emit one localized CLI line from the ``cli_out`` namespace."""
    _emit(t(f"cli_out.{key}", detect_language(), **vars_))


def _root() -> Path:
    return paths.project_root()


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_version(_args: argparse.Namespace) -> int:
    _emit(version_string())
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    root = _root()
    report = install.init_project(root, dry_run=args.dry_run, level=args.level)
    lang = detect_language()
    if args.json:
        _json(
            {
                "project": report.project,
                "detected": report.detected,
                "changed": report.changed,
                "skipped": report.skipped,
                "pinned": report.pinned_sha256,
            }
        )
        return 0
    _emit(t("cli.init_done", lang, project=report.project))
    if args.dry_run:
        _emit(t("cli.dry_run", lang))
    for changed in report.changed:
        _emit(f"  + {changed}")
    for backup in report.backups:
        _emit("  ~ " + t("cli_out.backup", lang, path=backup))
    if report.skipped and not args.dry_run:
        for skipped in report.skipped:
            _emit("  ! " + t("cli_out.skipped_malformed", lang, path=skipped))
        return 1
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    root = _root()
    changed = install.uninstall_project(root, dry_run=args.dry_run)
    if args.json:
        _json({"changed": changed})
        return 0
    _emit(t("cli.uninstall_done", detect_language()))
    for path in changed:
        _emit(f"  - {path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    data = install.status(root)
    pinned = read_pinned(root)
    settings = merge_pinned(load_settings(root), pinned)
    data.update(
        {
            "strictness": settings.strictness,
            "language": detect_language(),
            "reviewed": is_reviewed(detect_language()),
            "paused": pause.is_paused(root),
        }
    )
    if args.json:
        _json(data)
        return 0
    lang = detect_language()
    dot = "●"
    _emit(f"{dot} AiProof by SYSIK — {t('status.armed', lang)}")
    _emit(f"  {t('status.mode', lang, mode=settings.strictness)}")
    _emit(f"  {t('status.project', lang, project=data['project'])}")
    state = t("doctor.ok", lang) if data["pinned_ok"] else str(data["pinned_reason"])
    _emit(f"  {t('tui.pinned', lang)}: {state}")
    agents = data.get("agents")
    agents_text = ", ".join(str(a) for a in agents) if isinstance(agents, list) else ""
    _emit(f"  {t('tui.agents', lang)}: {agents_text or t('cli_out.none_detected', lang)}")
    if data["paused"]:
        _emit(t("cli_out.paused", lang))
    return 0


def _sessions(root: Path) -> list[str]:
    seen: list[str] = []
    for record in LedgerStore(root).records():
        sid = record.get("session")
        if isinstance(sid, str) and sid not in seen:
            seen.append(sid)
    return seen


def cmd_sessions(args: argparse.Namespace) -> int:
    root = _root()
    sessions = _sessions(root)
    if args.json:
        _json(sessions)
        return 0
    for sid in sessions[-20:]:
        _emit(sid)
    if not sessions:
        _emit(t("tui.no_sessions_recorded", detect_language()))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root = _root()
    session = args.session or LedgerStore(root).last_session()
    if session is None:
        _emit(t("tui.no_sessions_recorded", detect_language()))
        return 1
    receipt = build_receipt(root, session)
    fmt = args.format
    lang = detect_language()
    if fmt == "json":
        _emit(render_json(receipt))
    elif fmt == "html":
        _emit(render_html(receipt, lang=lang))
    else:
        _emit(render_md(receipt, lang=lang))
    return 0


def cmd_ledger(args: argparse.Namespace) -> int:
    root = _root()
    result = verify.verify(root)
    if args.json:
        _json(
            {
                "ok": result.ok,
                "checked": result.checked,
                "segments": result.segments,
                "head": result.head,
                "reason": result.reason,
            }
        )
        return 0 if result.ok else 1
    _emit(result.summary())
    return 0 if result.ok else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    root = _root()
    lines = doctor.run(root, detect_language())
    if args.json:
        _json(doctor.as_dict(lines))
        return 1 if doctor.has_failures(lines) else 0
    lang = detect_language()
    for line in lines:
        mark = {"ok": "✓", "warn": "!", "fail": "✗"}.get(line.level, "?")
        suffix = f"  ({t('doctor.fix_hint', lang, hint=line.hint)})" if line.hint else ""
        _emit(f"[{mark}] {line.label}{suffix}")
    return 1 if doctor.has_failures(lines) else 0


def cmd_bench(args: argparse.Namespace) -> int:
    result = run_scenarios()
    if args.json:
        _json(result.as_dict())
        return 0
    if args.md:
        _emit(result.to_md())
        return 0
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="AiProof benchmark")
        for column in ("#", "scenario", "expected", "actual", "result", "ms"):
            table.add_column(column)
        for o in result.outcomes:
            verdict = "caught" if o.caught else ("MISSED" if o.expected_block else "FALSE POS")
            table.add_row(
                str(o.index),
                o.name,
                "block" if o.expected_block else "allow",
                "block" if o.blocked else "allow",
                verdict,
                f"{o.latency_ms:.0f}",
            )
        console.print(table)
        console.print(
            f"detection {result.detection_rate:.0%} · false-positives "
            f"{result.false_positive_rate:.0%} · median {result.median_latency_ms:.0f} ms"
        )
        return 0
    except ModuleNotFoundError:
        for o in result.outcomes:
            verdict = "caught" if o.caught else "MISSED"
            _emit(f"{o.index:>2} {verdict:<7} {o.name}")
        _emit(
            f"detection {result.detection_rate:.0%} · fp {result.false_positive_rate:.0%} "
            f"· median {result.median_latency_ms:.0f} ms"
        )
        return 0


def cmd_scan(args: argparse.Namespace) -> int:
    root = _root()
    allow: Allowlist = load_allowlist(paths.project_allow_path(root))
    allow.compile()
    findings = []
    if args.tree:
        findings += scan_tree(root, allow)
    if args.instructions:
        findings += scan_instruction_files(root, allow)
    if args.histories:
        findings += scan_agent_histories(allow)
    if not (args.tree or args.instructions or args.histories):
        findings += scan_diff(root, allow)
    payload = [f.as_dict() for f in findings]
    if args.json:
        _json(payload)
        return 0
    if not findings:
        _emit(t("tui.no_secrets", detect_language()))
        return 0
    for finding in findings:
        _emit(f"{finding.type}  {finding.path}:{finding.line}  [{finding.fingerprint}]")
    return 1


def cmd_report(args: argparse.Namespace) -> int:
    return cmd_show(args)


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify ad-hoc claims text (agent self-check)."""
    root = _root()
    settings = merge_pinned(load_settings(root), read_pinned(root))
    claims = extract_claims(args.text)
    ctx = CheckContext(root=root, settings=settings, session="cli", claims=claims)
    decision = decide(ctx, agent_lang=settings.agent_message_language, integrity=False)
    if args.json:
        _json(decision.as_dict())
        return 0
    for result in decision.results:
        _emit(f"[{result.verdict}] {result.claim.type}: {result.reason}")
    for finding in decision.findings:
        _emit(f"[{finding.verdict}] {finding.check}: {finding.reason}")
    if decision.block:
        _emit(decision.reason)
    return 1 if decision.block else 0


def cmd_pin(args: argparse.Namespace) -> int:
    from aiproof.guard.pin import repin

    try:
        digest = repin(_root(), load_settings(_root()))
    except HumanOnlyError as exc:
        _emit(str(exc))
        return 2
    _emit(f"{t('tui.pinned', detect_language())}: {digest[:16]}…")
    return 0


def cmd_pause(args: argparse.Namespace) -> int:
    try:
        until = pause.pause(_root(), args.minutes)
    except HumanOnlyError as exc:
        _emit(str(exc))
        return 2
    _say("paused_for", minutes=args.minutes, until=until)
    return 0


def cmd_resume(_args: argparse.Namespace) -> int:
    try:
        pause.resume(_root())
    except HumanOnlyError as exc:
        _emit(str(exc))
        return 2
    _say("resumed")
    return 0


def cmd_agents(args: argparse.Namespace) -> int:
    if args.json:
        _json(
            [
                {
                    "id": a.id,
                    "name": a.name,
                    "vendor": a.vendor,
                    "kind": str(a.kind),
                    "support": str(a.support),
                    "status": str(a.status),
                    "verified": a.verified,
                }
                for a in AGENTS
            ]
        )
        return 0
    for support in (Support.NATIVE_HOOKS, Support.MCP_ONLY, Support.WRAPPER):
        _emit(f"== {support} ==")
        for agent in by_support(support):
            mark = "✓" if agent.status is Status.VERIFIED else "·"
            _emit(f"  {mark} {agent.id:<16} {agent.name} ({agent.vendor})")
    return 0


def cmd_lang(args: argparse.Namespace) -> int:
    if not args.code:
        _emit(f"{t('cli_out.current', detect_language())}: {detect_language()}")
        for code in KNOWN_LANGS:
            if code in available():
                suffix = (
                    ""
                    if is_reviewed(code)
                    else " " + t("tui.machine_translated", detect_language())
                )
                _emit(f"  {code}{suffix}")
        return 0
    _set_global("language", args.code)
    _say("lang_set", code=args.code)
    return 0


def cmd_theme(args: argparse.Namespace) -> int:
    if not args.name:
        _say("themes", themes=", ".join(THEMES))
        return 0
    if args.name not in THEMES:
        _say("unknown_theme", name=args.name, themes=", ".join(THEMES))
        return 2
    _set_global("theme", args.name)
    _say("theme_set", name=args.name)
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    target = paths.log_path()
    if not target.is_file():
        _emit(t("tui.no_logs", detect_language()))
        return 0
    lines = target.read_text(encoding="utf-8").splitlines()
    if args.lines > 0:
        lines = lines[-args.lines :]
    for line in lines:
        _emit(line)
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    from aiproof.maintenance import update

    if not args.check:
        _say("update_hint")
        return 0
    info = update.check()
    if args.json:
        _json(
            {
                "current": info.current,
                "latest": info.latest,
                "newer": info.newer,
                "error": info.error,
            }
        )
        return 0 if info.ok else 1
    if not info.ok:
        _say("update_failed", error=info.error)
        return 1
    state = (
        t("cli_out.update_available", detect_language())
        if info.newer
        else t("cli_out.up_to_date", detect_language())
    )
    _say("update_status", current=info.current, latest=info.latest, state=state)
    return 0


def cmd_about(_args: argparse.Namespace) -> int:
    _emit(version_string())
    _emit(t("about.license"))
    _emit(t("tagline"))
    return 0


def cmd_correct(args: argparse.Namespace) -> int:
    root = _root()
    from aiproof.learn import record_correction

    try:
        correction, created = record_correction(root, args.text)
    except ValueError as exc:
        _emit(str(exc))
        return 2
    if getattr(args, "json", False):
        _json(correction.as_dict() | {"created": created})
    else:
        state = t(
            "cli_out.correction_new" if created else "cli_out.correction_duplicate",
            detect_language(),
        )
        _say("correction_recorded", id=correction.id, state=state, text=correction.text)
    return 0


def _summarize_event(record: dict[str, Any]) -> str:
    payload = record.get("payload", {})
    if not isinstance(payload, dict):
        return ""
    event = record.get("event")
    if event == "gate_decision":
        return "BLOCK" if payload.get("block") else "ok"
    if event == "claims_extracted":
        return f"claims={payload.get('count')}"
    if event in ("tool_pre", "tool_post"):
        return str(payload.get("command", ""))[:80]
    if event == "tamper_attempt":
        return str(payload.get("reason", ""))[:80]
    if event == "correction":
        return str(payload.get("text", ""))[:80]
    return ""


def cmd_learn(args: argparse.Namespace) -> int:
    from aiproof import paths
    from aiproof.guard.pin import HumanOnlyError, require_human
    from aiproof.learn import (
        backtest,
        compile_all,
        list_corrections,
        load_rules,
        save_rules,
        set_enabled,
        upsert_rule,
        write_export,
    )

    root = _root()
    action = args.action or "list"
    rules = load_rules(paths.rules_path(root))

    if action == "list":
        corrections = list_corrections(root)
        if getattr(args, "json", False):
            _json(
                {
                    "corrections": [c.as_dict() for c in corrections],
                    "rules": [rule.to_dict() | {"id": rule.id} for rule in rules],
                }
            )
            return 0
        _say("learn_summary", corrections=len(corrections), rules=len(rules))
        for correction in corrections:
            _emit(f"  {correction.id} [{correction.topic}] {correction.text}")
        for existing_rule in rules:
            state = "enabled" if existing_rule.enabled else "disabled"
            _emit(
                f"  {existing_rule.id} [{state}, {existing_rule.severity}] "
                f"{existing_rule.description}"
            )
        if not corrections and not rules:
            _emit("  " + t("cli_out.learn_none", detect_language()))
        return 0

    if action == "compile":
        candidates = compile_all(root, rules)
        if args.write:
            for candidate in candidates:
                if candidate.rule is not None:
                    rules = upsert_rule(rules, candidate.rule)
            save_rules(paths.rules_path(root), rules)
        if getattr(args, "json", False):
            _json([candidate.as_dict() for candidate in candidates])
            return 0
        if not candidates:
            _say("learn_nothing")
            return 0
        lang = detect_language()
        for candidate in candidates:
            mark = t(
                "cli_out.learn_compiled" if candidate.compiled else "cli_out.learn_advisory", lang
            )
            _emit(
                "  "
                + t(
                    "cli_out.learn_candidate",
                    lang,
                    id=candidate.correction_id,
                    state=mark,
                    reason=candidate.reason,
                )
            )
            if candidate.rule is not None:
                _emit(
                    f"      {candidate.rule.id} ({candidate.rule.severity}) "
                    f"scope={candidate.rule.scope}"
                )
        if args.write and any(candidate.compiled for candidate in candidates):
            _say("learn_saved")
        return 0

    if action in ("enable", "disable"):
        try:
            require_human(action)
        except HumanOnlyError as exc:
            _emit(str(exc))
            return 2
        if not args.rule_id:
            _say("learn_usage", action=action)
            return 2
        try:
            rules = set_enabled(rules, args.rule_id, action == "enable")
        except KeyError:
            _say("unknown_rule", id=args.rule_id)
            return 1
        save_rules(paths.rules_path(root), rules)
        LedgerStore(root).append(
            "rule_toggle",
            {"rule": args.rule_id, "enabled": action == "enable"},
            session="human",
        )
        state = t("tui.enabled" if action == "enable" else "tui.disabled", detect_language())
        _say("rule_toggled", id=args.rule_id, state=state)
        return 0

    if action == "backtest":
        if not args.rule_id:
            _say("learn_backtest_usage")
            return 2
        rule = next((item for item in rules if item.id == args.rule_id), None)
        if rule is None:
            _say("unknown_rule", id=args.rule_id)
            return 1
        result = backtest(root, rule)
        if getattr(args, "json", False):
            _json(result.as_dict())
            return 0
        _say(
            "learn_backtest",
            id=rule.id,
            caught=result.would_have_caught,
            scanned=result.commits_scanned,
            false_positives=result.false_positives,
        )
        for sample in result.samples:
            _emit(f"  {sample['path']}:{sample['line']} {sample['text']}")
        _emit(result.note)
        return 0

    if action == "export":
        target = args.target or "AGENTS.md"
        try:
            path, changed = write_export(root, rules, target=target, lang=detect_language())
        except ValueError as exc:
            _emit(str(exc))
            return 2
        _say("export_wrote" if changed else "export_unchanged", path=path)
        return 0

    _say("unknown_action", action=action)
    return 2


def cmd_checks(args: argparse.Namespace) -> int:
    from aiproof.checks import ALL_CHECK_NAMES
    from aiproof.config import write_pinned
    from aiproof.guard.pin import HumanOnlyError, require_human

    root = _root()
    settings = merge_pinned(load_settings(root), read_pinned(root))

    if args.enable or args.disable or args.strictness:
        try:
            require_human("checks")
        except HumanOnlyError as exc:
            _emit(str(exc))
            return 2
        enabled = list(settings.enabled_checks)
        for name in args.enable or []:
            if name not in ALL_CHECK_NAMES:
                _say("unknown_check", name=name)
                return 1
            if name not in enabled:
                enabled.append(name)
        for name in args.disable or []:
            if name in enabled:
                enabled.remove(name)
        settings.enabled_checks = tuple(enabled)
        if args.strictness:
            settings.strictness = args.strictness
        write_pinned(root, settings)
        LedgerStore(root).append(
            "rule_toggle",
            {"checks": list(settings.enabled_checks), "strictness": settings.strictness},
            session="human",
        )

    if getattr(args, "json", False):
        _json(
            {
                "strictness": settings.strictness,
                "checks": [
                    {"name": name, "enabled": name in settings.enabled_checks}
                    for name in ALL_CHECK_NAMES
                ],
            }
        )
        return 0
    _emit(f"{t('tui.strictness', detect_language())}: {settings.strictness}")
    for name in ALL_CHECK_NAMES:
        mark = "x" if name in settings.enabled_checks else " "
        _emit(f"  [{mark}] {name}")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    import time

    root = _root()
    store = LedgerStore(root)
    initial = store.records()
    seen = max(0, len(initial) - max(1, args.lines))
    if args.once:
        for record in initial[seen:]:
            _emit(_watch_line(record, getattr(args, "json", False)))
        return 0
    for record in initial[seen:]:
        _emit(_watch_line(record, getattr(args, "json", False)))
    seen = len(initial)
    try:
        while True:
            time.sleep(0.5)
            records = store.records()
            for record in records[seen:]:
                _emit(_watch_line(record, getattr(args, "json", False)))
            seen = len(records)
    except KeyboardInterrupt:
        return 0


def _watch_line(record: dict[str, Any], as_json: bool) -> str:
    if as_json:
        return json.dumps(record, ensure_ascii=False, sort_keys=True)
    return (
        f"{record.get('ts', '')} {record.get('event', '?')!s:<14} "
        f"{record.get('session', '')}  {_summarize_event(record)}"
    )


def cmd_setup(args: argparse.Namespace) -> int:
    from aiproof.adapters import detect_all
    from aiproof.maintenance import install

    root = _root()
    detected = [adapter.id for adapter in detect_all(root)]
    _say("project", project=root)
    _say(
        "agents_detected",
        agents=", ".join(detected) or t("cli_out.agents_assumed", detect_language()),
    )
    if args.dry_run or not args.yes:
        _say("setup_plan")
        _say("setup_rerun")
        return 0

    report = install.init_project(root)
    for changed in report.changed:
        _emit(f"  + {changed}")
    for backup in report.backups:
        _emit("  ~ " + t("cli_out.backup", detect_language(), path=backup))
    _emit(f"{t('tui.pinned', detect_language())}: {report.pinned_sha256[:16]}...")

    settings = merge_pinned(load_settings(root), read_pinned(root))
    claims = extract_claims("all tests pass")
    decision = decide(
        CheckContext(root=root, settings=settings, session="setup", claims=claims),
        agent_lang=settings.agent_message_language,
        integrity=False,
    )
    state = t(
        "cli_out.setup_blocked" if decision.block else "cli_out.setup_recorded", detect_language()
    )
    _say("setup_self_test", state=state)
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    from aiproof.adapters import AGENTS
    from aiproof.adapters.claude_code import ClaudeCodeAdapter
    from aiproof.adapters.generic_mcp import McpAdapter
    from aiproof.adapters.registry import Support

    root = _root()
    if args.list_ides:
        for listed in AGENTS:
            _emit(f"{listed.id:<16} {listed.support!s:<13} {listed.status!s:<10} {listed.name}")
        return 0

    targets = [agent.id for agent in AGENTS] if args.all else [args.ide] if args.ide else []
    if not targets:
        _say("install_usage")
        return 2

    known = {agent.id: agent for agent in AGENTS}
    for target in targets:
        target_agent = known.get(str(target))
        if target_agent is None:
            _say("install_unknown_ide", name=target)
            return 1
        if target_agent.id == "claude-code":
            result = ClaudeCodeAdapter().install(root, dry_run=args.dry_run)
            state = t("cli_out.planned" if args.dry_run else "cli_out.installed", detect_language())
            _say("install_hooks", state=state)
        elif target_agent.support in (Support.NATIVE_HOOKS, Support.MCP_ONLY):
            result = McpAdapter().install(root, dry_run=args.dry_run)
            state = t("cli_out.planned" if args.dry_run else "cli_out.written", detect_language())
            _say("install_mcp", agent=target_agent.id, state=state)
        else:
            _say("install_wrapper", agent=target_agent.id)
            continue
        for changed in result.changed:
            _emit(f"  + {changed}")
        for backup in result.backups:
            _emit(f"  ~ backup {backup}")
        for skipped in result.skipped:
            _emit("  = " + t("cli_out.install_skipped", detect_language(), path=skipped))
    return 0


def cmd_off(_args: argparse.Namespace) -> int:
    from aiproof.guard.pin import HumanOnlyError, require_human
    from aiproof.maintenance import install

    try:
        require_human("off")
    except HumanOnlyError as exc:
        _emit(str(exc))
        return 2
    for changed in install.uninstall_project(_root()):
        _emit(f"  - {changed}")
    _say("off_done")
    return 0


def cmd_keys(args: argparse.Namespace) -> int:
    from aiproof.tui.keys import ACTIONS

    if getattr(args, "json", False):
        _json(ACTIONS)
        return 0
    _emit(t("cli_out.keys_title", detect_language()))
    for key in ("w", "ц", "s", "ы", "q", "й", "l", "д", "t", "е", "r", "к", "?", "/"):
        _emit(
            "  "
            + t("cli_out.keys_line", detect_language(), key=repr(key), action=ACTIONS.get(key, "?"))
        )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from aiproof.adapters.wrapper import run_wrapped

    return run_wrapped(args.command, _root())


def cmd_hook(args: argparse.Namespace) -> int:
    from aiproof.hooks import entry

    return entry.main([args.event])


def cmd_mcp(_args: argparse.Namespace) -> int:
    from aiproof.mcp import server

    return server.main()


def cmd_tui(args: argparse.Namespace) -> int:
    from aiproof.tui.app import run_tui

    return run_tui(ascii_only=args.ascii, no_anim=args.no_anim)


def _set_global(key: str, value: str) -> None:
    import tomllib

    import tomli_w

    path = paths.global_config_path()
    data: dict[str, Any] = {}
    if path.is_file():
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    data[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tomli_w.dumps(data).encode("utf-8"))


# --------------------------------------------------------------------------- #
# argument parsing
# --------------------------------------------------------------------------- #
def build_parser(lang: str | None = None) -> argparse.ArgumentParser:
    """Build the full argparse tree (help text localized via i18n)."""

    def h(key: str) -> str:
        return t(f"help.{key}", lang)

    parser = argparse.ArgumentParser(prog="aiproof", description=h("description"))
    parser.add_argument("--version", action="version", version=version_string())
    parser.add_argument("--json", action="store_true", help=h("json"))
    parser.add_argument("--lang", choices=KNOWN_LANGS, help=h("lang"))
    subs = parser.add_subparsers(dest="command")

    subs.add_parser("version", help=h("version")).set_defaults(func=cmd_version)
    subs.add_parser("about", help=h("about")).set_defaults(func=cmd_about)

    p_init = subs.add_parser("init", help=h("init"))
    p_init.add_argument("--dry-run", action="store_true")
    p_init.add_argument("--level", choices=("project", "local", "user"), default="project")
    p_init.set_defaults(func=cmd_init)

    p_un = subs.add_parser("uninstall", help=h("uninstall"))
    p_un.add_argument("--dry-run", action="store_true")
    p_un.set_defaults(func=cmd_uninstall)

    subs.add_parser("status", help=h("status")).set_defaults(func=cmd_status)
    subs.add_parser("sessions", help=h("sessions")).set_defaults(func=cmd_sessions)

    p_show = subs.add_parser("show", help=h("show"))
    p_show.add_argument("session", nargs="?")
    p_show.add_argument("--format", choices=("json", "html", "md"), default="md")
    p_show.set_defaults(func=cmd_show)

    p_rep = subs.add_parser("report", help=h("report"))
    p_rep.add_argument("session", nargs="?")
    p_rep.add_argument("--format", choices=("json", "html", "md"), default="md")
    p_rep.set_defaults(func=cmd_report)

    ledger = subs.add_parser("ledger", help=h("ledger"))
    ledger_subs = ledger.add_subparsers(dest="ledger_cmd")
    ledger_subs.add_parser("verify", help=h("ledger_verify")).set_defaults(func=cmd_ledger)
    ledger.set_defaults(func=cmd_ledger)

    subs.add_parser("doctor", help=h("doctor")).set_defaults(func=cmd_doctor)

    p_bench = subs.add_parser("bench", help=h("bench"))
    p_bench.add_argument("--md", action="store_true")
    p_bench.set_defaults(func=cmd_bench)

    p_scan = subs.add_parser("scan", help=h("scan"))
    p_scan.add_argument("--tree", action="store_true")
    p_scan.add_argument("--instructions", action="store_true")
    p_scan.add_argument("--histories", action="store_true")
    p_scan.set_defaults(func=cmd_scan)

    p_verify = subs.add_parser("verify", help=h("verify"))
    p_verify.add_argument("text")
    p_verify.set_defaults(func=cmd_verify)

    subs.add_parser("pin", help=h("pin")).set_defaults(func=cmd_pin)

    p_pause = subs.add_parser("pause", help=h("pause"))
    p_pause.add_argument("minutes", type=int, nargs="?", default=30)
    p_pause.set_defaults(func=cmd_pause)

    subs.add_parser("resume", help=h("resume")).set_defaults(func=cmd_resume)

    p_agents = subs.add_parser("agents", help=h("agents"))
    p_agents.set_defaults(func=cmd_agents)

    p_lang = subs.add_parser("lang", help=h("lang_cmd"))
    p_lang.add_argument("code", nargs="?")
    p_lang.set_defaults(func=cmd_lang)

    p_theme = subs.add_parser("theme", help=h("theme"))
    p_theme.add_argument("name", nargs="?")
    p_theme.set_defaults(func=cmd_theme)

    p_logs = subs.add_parser("logs", help=h("logs"))
    p_logs.add_argument("--lines", type=int, default=40)
    p_logs.set_defaults(func=cmd_logs)

    p_update = subs.add_parser("update", help=h("update"))
    p_update.add_argument("--check", action="store_true")
    p_update.set_defaults(func=cmd_update)

    p_correct = subs.add_parser("correct", help=h("correct"))
    p_correct.add_argument("text")
    p_correct.set_defaults(func=cmd_correct)

    p_learn = subs.add_parser("learn", help=h("learn"))
    p_learn.add_argument(
        "action",
        nargs="?",
        choices=("list", "compile", "enable", "disable", "backtest", "export"),
        default="list",
    )
    p_learn.add_argument("rule_id", nargs="?")
    p_learn.add_argument("--write", action="store_true")
    p_learn.add_argument("--target", default="AGENTS.md")
    p_learn.set_defaults(func=cmd_learn)

    p_checks = subs.add_parser("checks", help=h("checks"))
    p_checks.add_argument("strictness", nargs="?", choices=STRICTNESS_PRESETS)
    p_checks.add_argument("--enable", action="append", metavar="NAME")
    p_checks.add_argument("--disable", action="append", metavar="NAME")
    p_checks.set_defaults(func=cmd_checks)

    p_watch = subs.add_parser("watch", help=h("watch"))
    p_watch.add_argument("--once", action="store_true")
    p_watch.add_argument("--lines", type=int, default=20)
    p_watch.set_defaults(func=cmd_watch)

    p_setup = subs.add_parser("setup", help=h("setup"))
    p_setup.add_argument("--yes", action="store_true")
    p_setup.add_argument("--dry-run", action="store_true")
    p_setup.set_defaults(func=cmd_setup)

    p_install = subs.add_parser("install", help=h("install"))
    p_install.add_argument("--ide")
    p_install.add_argument("--all", action="store_true")
    p_install.add_argument("--dry-run", action="store_true")
    p_install.add_argument("--list-ides", action="store_true")
    p_install.set_defaults(func=cmd_install)

    subs.add_parser("off", help=h("off")).set_defaults(func=cmd_off)
    subs.add_parser("keys", help=h("keys")).set_defaults(func=cmd_keys)

    p_receipt = subs.add_parser("receipt", help=h("receipt"))
    p_receipt.add_argument("session", nargs="?")
    p_receipt.add_argument("--format", choices=("json", "html", "md"), default="md")
    p_receipt.set_defaults(func=cmd_show)

    p_run = subs.add_parser("run", help=h("run"))
    p_run.add_argument("command", nargs=argparse.REMAINDER)
    p_run.set_defaults(func=cmd_run)

    p_hook = subs.add_parser("hook", help=h("hook"))
    p_hook.add_argument("event")
    p_hook.set_defaults(func=cmd_hook)

    subs.add_parser("mcp", help=h("mcp")).set_defaults(func=cmd_mcp)

    p_tui = subs.add_parser("tui", help=h("tui"))
    p_tui.add_argument("--ascii", action="store_true")
    p_tui.add_argument("--no-anim", action="store_true")
    p_tui.set_defaults(func=cmd_tui)

    # Allow ``--json`` after the subcommand too. SUPPRESS keeps a value set
    # *before* the subcommand (``aiproof --json bench``) from being clobbered.
    _no_json = {"run", "hook", "mcp", "tui", "pin", "pause", "resume"}
    for _name in subs.choices:
        if _name not in _no_json:
            subs.choices[_name].add_argument(
                "--json",
                action="store_true",
                default=argparse.SUPPRESS,
                help=h("json"),
            )
    ledger_subs.choices["verify"].add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help=h("json"),
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch."""
    raw = list(argv) if argv is not None else sys.argv[1:]
    # Let ``--lang`` affect help text and output for this very run.
    for index, token in enumerate(raw):
        if token == "--lang" and index + 1 < len(raw):
            os.environ["AIPROOF_LANG"] = raw[index + 1]
        elif token.startswith("--lang="):
            os.environ["AIPROOF_LANG"] = token.split("=", 1)[1]
    parser = build_parser()
    args = parser.parse_args(raw)
    if getattr(args, "lang", None):
        os.environ["AIPROOF_LANG"] = args.lang
    func = getattr(args, "func", None)
    if func is None:
        if not sys.stdin.isatty():
            parser.print_help()
            return 0
        return cmd_tui(argparse.Namespace(ascii=False, no_anim=False))
    result: int = func(args)
    return result


__all__ = ["__author__", "__version__", "build_parser", "main"]
