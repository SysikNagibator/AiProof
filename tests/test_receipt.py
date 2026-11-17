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
    # Tamper attempts are part of the receipt, so HTML must render them too.
    assert "protected path" in html


def test_receipt_md_is_localized(tmp_path: Path) -> None:
    session = _seed(tmp_path)
    md = render_md(build_receipt(tmp_path, session), lang="ru")
    assert "Квитанция AiProof" in md
    assert "цепочка проверена" in md


def test_receipt_html_lang_attribute(tmp_path: Path) -> None:
    session = _seed(tmp_path)
    html = render_html(build_receipt(tmp_path, session), lang="de")
    assert '<html lang="de">' in html
    assert "AiProof-Beleg" in html


def test_receipt_detects_tamper(tmp_path: Path) -> None:
    session = _seed(tmp_path)
    from aiproof import paths

    ledger = paths.ledger_path(tmp_path)
    ledger.write_text(ledger.read_text().replace("true", "false"), encoding="utf-8")
    assert build_receipt(tmp_path, session).verified is False


def test_receipt_survives_wrong_payload_types(tmp_path: Path) -> None:
    """A parseable but schema-broken ledger must not crash the renderers."""
    store = LedgerStore(tmp_path)
    store.append("session_start", {"cwd": str(tmp_path)}, session="s2")
    store.append(
        "check_result",
        {
            "results": "not-a-list",
            "findings": [42, {"check": "x", "verdict": "fail", "reason": "y"}],
        },
        session="s2",
    )
    store.append(
        "check_result",
        {
            "results": [{"claim": "not-a-dict", "verdict": "fail", "reason": "z"}],
            "findings": None,
        },
        session="s2",
    )
    receipt = build_receipt(tmp_path, "s2")
    assert len(receipt.results) == 1
    assert len(receipt.findings) == 1
    assert "z" in render_md(receipt)
    assert "z" in render_html(receipt)
