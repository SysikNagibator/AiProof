"""Session receipt: claims vs evidence, verdicts, tamper and secret findings."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiproof.ledger import chain, verify
from aiproof.ledger.store import LedgerStore


@dataclass(slots=True)
class Receipt:
    """A structured, exportable session summary."""

    session: str
    project: str
    chain_head: str
    verified: bool
    results: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    tamper: list[dict[str, Any]]
    decisions: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON representation."""
        return {
            "v": 1,
            "generated": chain.now_iso(),
            "session": self.session,
            "project": self.project,
            "chain_head": self.chain_head,
            "verified": self.verified,
            "results": self.results,
            "findings": self.findings,
            "tamper": self.tamper,
            "decisions": self.decisions,
        }


def build_receipt(root: Path, session: str) -> Receipt:
    """Collect everything known about a session into a receipt."""
    store = LedgerStore(root)
    results: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    tamper: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for record in store.records(session=session):
        payload = record.get("payload", {})
        event = record.get("event")
        if event == "check_result" and isinstance(payload, dict):
            results.extend(payload.get("results", []))
            findings.extend(payload.get("findings", []))
        elif event == "tamper_attempt":
            tamper.append(payload if isinstance(payload, dict) else {})
        elif event == "gate_decision":
            decisions.append(payload if isinstance(payload, dict) else {})
    result = verify.verify(root)
    return Receipt(
        session=session,
        project=str(root),
        chain_head=result.head,
        verified=result.ok,
        results=results,
        findings=findings,
        tamper=tamper,
        decisions=decisions,
    )


def render_json(receipt: Receipt) -> str:
    """Render a receipt as pretty JSON (sorted keys)."""
    return json.dumps(receipt.as_dict(), indent=2, sort_keys=True, ensure_ascii=False)


def render_md(receipt: Receipt) -> str:
    """Render a receipt as Markdown."""
    lines = [
        f"# AiProof receipt — session `{receipt.session}`",
        "",
        f"- project: `{receipt.project}`",
        f"- chain verified: {'yes' if receipt.verified else 'NO'}",
        f"- chain head: `{receipt.chain_head[:16]}…`",
        "",
        "## Claims vs evidence",
        "",
        "| claim | verdict | evidence |",
        "| --- | --- | --- |",
    ]
    for result in receipt.results:
        claim = result.get("claim", {})
        lines.append(
            f"| {claim.get('type', '?')}: {claim.get('text', '')} "
            f"| {result.get('verdict', '?')} | {result.get('reason', '')} |"
        )
    if receipt.findings:
        lines += ["", "## Integrity findings", ""]
        for finding in receipt.findings:
            lines.append(
                f"- **{finding.get('check')}** ({finding.get('verdict')}): {finding.get('reason')}"
            )
    if receipt.tamper:
        lines += ["", "## Tamper attempts", ""]
        for attempt in receipt.tamper:
            lines.append(f"- {attempt.get('tool')}: {attempt.get('reason')}")
    return "\n".join(lines) + "\n"


def render_html(receipt: Receipt) -> str:
    """Render a self-contained, printable, dark/light-aware HTML receipt."""
    rows = []
    for result in receipt.results:
        claim = result.get("claim", {})
        rows.append(
            "<tr><td>{}</td><td class='{}'>{}</td><td>{}</td></tr>".format(
                html.escape(f"{claim.get('type', '?')}: {claim.get('text', '')}"),
                html.escape(str(result.get("verdict", ""))),
                html.escape(str(result.get("verdict", ""))),
                html.escape(str(result.get("reason", ""))),
            )
        )
    findings = "".join(
        f"<li><b>{html.escape(str(f.get('check')))}</b> ({html.escape(str(f.get('verdict')))}): "
        f"{html.escape(str(f.get('reason')))}</li>"
        for f in receipt.findings
    )
    badge = "✅ verified" if receipt.verified else "❌ chain broken"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>AiProof receipt</title>
<style>
 :root {{ color-scheme: light dark; }}
 body {{ font: 15px/1.5 system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
 h1 {{ font-size: 1.4rem; }}
 table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
 th, td {{ border: 1px solid #8884; padding: .4rem .6rem; text-align: left; }}
 .pass {{ color: #1a7f37; }} .fail {{ color: #cf222e; }} .unknown {{ color: #9a6700; }}
 footer {{ color: #888; font-size: .85rem; margin-top: 2rem; }}
</style></head>
<body>
<h1>AiProof receipt <small>by SYSIK</small></h1>
<p>session <code>{html.escape(receipt.session)}</code> · {badge} ·
head <code>{html.escape(receipt.chain_head[:16])}</code></p>
<table><thead><tr><th>claim</th><th>verdict</th><th>evidence</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table>
{"<h2>Integrity findings</h2><ul>" + findings + "</ul>" if findings else ""}
<footer>Generated locally by AiProof. No data left this machine.</footer>
</body></html>
"""
