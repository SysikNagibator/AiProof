"""Benchmark runner: executes the scenarios and aggregates honest numbers."""

from __future__ import annotations

import statistics
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aiproof.bench.harness import Outcome
from aiproof.bench.scenarios import SCENARIOS


@dataclass(slots=True)
class BenchResult:
    """Aggregated, real benchmark numbers."""

    outcomes: list[Outcome] = field(default_factory=list)
    detection_rate: float = 0.0
    false_positive_rate: float = 0.0
    median_latency_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe mapping."""
        return {
            "detection_rate": round(self.detection_rate, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "median_latency_ms": round(self.median_latency_ms, 1),
            "scenarios": [
                {
                    "id": o.index,
                    "name": o.name,
                    "blocked": o.blocked,
                    "expected_block": o.expected_block,
                    "caught": o.caught,
                    "latency_ms": round(o.latency_ms, 1),
                    "note": o.note,
                }
                for o in self.outcomes
            ],
        }

    def to_md(self) -> str:
        """Render the README benchmark table from real results."""
        lines = [
            "| # | scenario | expected | AiProof | result | ms |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for o in self.outcomes:
            result = "caught" if o.caught else ("MISSED" if o.expected_block else "FALSE POSITIVE")
            lines.append(
                f"| {o.index} | {o.name} | "
                f"{'block' if o.expected_block else 'allow'} | "
                f"{'block' if o.blocked else 'allow'} | {result} | {o.latency_ms:.0f} |"
            )
        lines += [
            "",
            f"**Detection rate:** {self.detection_rate:.0%}  ",
            f"**False-positive rate:** {self.false_positive_rate:.0%}  ",
            f"**Median latency:** {self.median_latency_ms:.0f} ms",
        ]
        return "\n".join(lines)


def run_scenarios() -> BenchResult:
    """Run every scenario in its own temp repo and aggregate results."""
    outcomes: list[Outcome] = []
    for index, name, fn in SCENARIOS:
        with tempfile.TemporaryDirectory(prefix="aiproof-bench-") as tmp:
            start = time.perf_counter()
            blocked, expected, note = fn(Path(tmp))
            latency = (time.perf_counter() - start) * 1000
        outcomes.append(Outcome(index, name, blocked, expected, latency, note))

    positives = [o for o in outcomes if o.expected_block]
    negatives = [o for o in outcomes if not o.expected_block]
    detection = sum(1 for o in positives if o.caught) / len(positives) if positives else 0.0
    false_pos = sum(1 for o in negatives if not o.caught) / len(negatives) if negatives else 0.0
    latencies = [o.latency_ms for o in outcomes] or [0.0]
    return BenchResult(
        outcomes=outcomes,
        detection_rate=detection,
        false_positive_rate=false_pos,
        median_latency_ms=statistics.median(latencies),
    )
