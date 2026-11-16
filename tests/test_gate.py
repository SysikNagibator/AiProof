"""Gate decision logic: strictness modes, cap, message content."""

from __future__ import annotations

from pathlib import Path

from aiproof.bench.harness import make_ctx, make_repo, tool_post
from aiproof.gate.gate import decide


def test_enforce_blocks_on_failure(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path)
    ctx = make_ctx(
        root, claims_text="all tests pass", strictness="enforce", start_commit=head, records=[]
    )
    decision = decide(ctx)
    assert decision.block
    assert decision.reason


def test_observe_never_blocks(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path)
    ctx = make_ctx(
        root, claims_text="all tests pass", strictness="observe", start_commit=head, records=[]
    )
    assert not decide(ctx).block


def test_warn_does_not_block_but_explains(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path)
    ctx = make_ctx(
        root, claims_text="all tests pass", strictness="warn", start_commit=head, records=[]
    )
    decision = decide(ctx)
    assert not decision.block
    assert decision.reason


def test_enforce_passes_honest_run(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path)
    ctx = make_ctx(
        root,
        claims_text="all tests pass",
        strictness="enforce",
        start_commit=head,
        records=[tool_post("pytest -q", "5 passed")],
    )
    assert not decide(ctx).block


def test_strict_blocks_on_unknown(tmp_path: Path) -> None:
    root, _head = make_repo(tmp_path)
    ctx = make_ctx(
        root, claims_text="added tests", strictness="strict", start_commit=None, records=[]
    )
    assert decide(ctx).block


def test_capped_blocks(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path)
    ctx = make_ctx(
        root,
        claims_text="all tests pass",
        strictness="enforce",
        start_commit=head,
        records=[tool_post("pytest -q", "5 passed")],
    )
    assert not decide(ctx).block
    assert decide(ctx, capped=True).block


def test_counts_present(tmp_path: Path) -> None:
    root, head = make_repo(tmp_path)
    ctx = make_ctx(
        root,
        claims_text="42 tests pass",
        strictness="enforce",
        start_commit=head,
        records=[tool_post("pytest -q", "31 passed")],
    )
    counts = decide(ctx).counts()
    assert counts["checks"] >= 1
    assert counts["fail"] >= 1
