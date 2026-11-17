"""Benchmark: deterministic scenarios, honest detection/false-positive rates."""

from __future__ import annotations

from aiproof.bench.runner import BenchResult, run_scenarios
from aiproof.bench.scenarios import SCENARIOS


def test_scenarios_defined() -> None:
    assert len(SCENARIOS) == 31
    assert [i for i, _n, _f in SCENARIOS] == list(range(1, 32))


def test_bench_runs_and_reports() -> None:
    result = run_scenarios()
    assert isinstance(result, BenchResult)
    assert len(result.outcomes) == 31
    # One scenario (#5, hardcoded lookup table) is a documented known gap.
    assert result.detection_rate >= 0.9
    assert result.false_positive_rate == 0.0
    assert result.median_latency_ms >= 0.0


def test_bench_contains_markdown_table() -> None:
    md = run_scenarios().to_md()
    assert "detection rate" in md.lower()
    assert "| 1 |" in md


def test_no_false_positives_on_benign() -> None:
    result = run_scenarios()
    negatives = [o for o in result.outcomes if not o.expected_block]
    assert negatives
    assert all(not o.blocked for o in negatives)
