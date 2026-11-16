"""Phase 2: turn corrections into executable checks (advisory otherwise)."""

from __future__ import annotations

from aiproof.learn.backtest import BacktestResult, backtest
from aiproof.learn.compile import Candidate, compile_all, compile_correction
from aiproof.learn.corrections import Correction, list_corrections, record_correction
from aiproof.learn.dsl import (
    Rule,
    apply_rule,
    apply_rules,
    load_rules,
    save_rules,
    set_enabled,
    upsert_rule,
)
from aiproof.learn.export import render_block, write_export

__all__ = [
    "BacktestResult",
    "Candidate",
    "Correction",
    "Rule",
    "apply_rule",
    "apply_rules",
    "backtest",
    "compile_all",
    "compile_correction",
    "list_corrections",
    "load_rules",
    "record_correction",
    "render_block",
    "save_rules",
    "set_enabled",
    "upsert_rule",
    "write_export",
]
