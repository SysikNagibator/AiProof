"""Receipts: build from the ledger and render json/md/html."""

from __future__ import annotations

from pathlib import Path

from aiproof.ledger.receipt import build_receipt, render_html, render_json, render_md
from aiproof.ledger.store import LedgerStore


def _seed(root: Path) -> str:
    store = LedgerStore(root)
    store.append("session_start", {"cwd": str(root), "start_commit": None}, session="s1")
    store.append(
        "check_result",
        {
            "results": [
                {
                    "claim": {
                        "type": "tests_pass",
                        "text": "all tests pass",
                        "language": "en",
                        "params": {},
                    },
                    "verdict": "fail",
                    "reason": "no test command observed",
                    "evidence": [],
                }
            ],
            "findings": [],
        },
        session="s1",
    )
    store.append("tamper_attempt", {"tool": "Bash", "reason": "protected path"}, session="s1")
    store.append("gate_decision", {"block": True, "counts": {"fail": 1}}, session="s1")
    return "s1"


def test_receipt_json_roundtrip(tmp_path: Path) -> None:
    session = _seed(tmp_path)
    receipt = build_receipt(tmp_path, session)
    rendered = render_json(receipt)
    assert '"session": "s1"' in rendered
    assert receipt.verified is True


def test_receipt_md_contains_claim(tmp_path: Path) -> None:
    session = _seed(tmp_path)
    md = render_md(build_receipt(tmp_path, session))
    assert "tests_pass" in md
    assert "chain verified: yes" in md


def test_receipt_html_is_self_contained(tmp_path: Path) -> None:
    session = _seed(tmp_path)
    html = render_html(build_receipt(tmp_path, session))
    assert html.startswith("<!doctype html>")
    assert "AiProof" in html


def test_receipt_detects_tamper(tmp_path: Path) -> None:
    session = _seed(tmp_path)
    from aiproof import paths

    ledger = paths.ledger_path(tmp_path)
    ledger.write_text(ledger.read_text().replace("true", "false"), encoding="utf-8")
    assert build_receipt(tmp_path, session).verified is False
