"""Check registry: claim checks and whole-session integrity checks."""

from __future__ import annotations

from types import ModuleType

from aiproof.checks import (
    commit_exists,
    config_integrity,
    file_changed,
    learn_rules,
    secrets_in_diff,
    test_tamper,
    tests_ran,
    todo_integrity,
)
from aiproof.claims.model import Claim

CLAIM_CHECKS: tuple[ModuleType, ...] = (commit_exists, file_changed, tests_ran)
INTEGRITY_CHECKS: tuple[ModuleType, ...] = (
    test_tamper,
    secrets_in_diff,
    todo_integrity,
    config_integrity,
    learn_rules,
)

ALL_CHECK_NAMES: tuple[str, ...] = tuple(m.NAME for m in CLAIM_CHECKS) + tuple(
    m.NAME for m in INTEGRITY_CHECKS
)


def claim_checks_for(claim: Claim) -> list[ModuleType]:
    """Return every claim check that applies to *claim*."""
    return [m for m in CLAIM_CHECKS if m.applies(claim)]


def integrity_checks(enabled: tuple[str, ...]) -> list[ModuleType]:
    """Return enabled integrity checks, preserving registry order."""
    return [m for m in INTEGRITY_CHECKS if m.NAME in enabled]
