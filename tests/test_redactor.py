"""Redactor: secrets never survive; benign lookalikes are not mangled."""

from __future__ import annotations

import pytest

from aiproof.redact.redactor import Allowlist, find_secrets, redact_json, redact_text

SECRETS = [
    "AKIAIOSFODNN7EXAMPLE",
    "ghp_" + "a" * 36,
    "glpat-" + "b" * 20,
    "sk-proj-" + "c" * 30,
    "sk-ant-" + "d" * 30,
    "xoxb-1234567890-abcdefghij",
    "AIza" + "e" * 35,
    "eyJhbGciOi.eyJzdWIiOi.abcdef123",
    "postgres://user:s3cr3tpw@localhost:5432/db",
    "Authorization: Bearer abcdef1234567890",
    "SG." + "f" * 22 + "." + "g" * 43,
]

BENIGN = [
    "def add(a, b):\n    return a + b\n",
    "0123456789abcdef0123456789abcdef01234567",  # git sha1
    "550e8400-e29b-41d4-a716-446655440000",  # uuid
    "sha256-" + "a" * 43,
    "The quick brown fox jumps over the lazy dog.",
]


@pytest.mark.parametrize("secret", SECRETS)
def test_secret_is_removed(secret: str) -> None:
    redacted = redact_text(f"value = {secret} end")
    assert secret not in redacted
    assert "REDACTED" in redacted


@pytest.mark.parametrize("text", BENIGN)
def test_benign_is_untouched(text: str) -> None:
    assert redact_text(text) == text


def test_placeholder_is_stable_and_opaque() -> None:
    secret = "AKIAIOSFODNN7EXAMPLE"
    a = redact_text(secret)
    b = redact_text(f"again {secret}")
    token = a.strip("[]").split(":")[-1].rstrip("]")
    assert token in b
    assert secret not in b


def test_allowlist_fingerprint() -> None:
    secret = "ghp_" + "a" * 36
    fp = find_secrets(secret)[0].fingerprint
    allow = Allowlist(fingerprints=(fp,))
    allow.compile()
    assert redact_text(secret, allow) == secret


def test_redact_json_recurses() -> None:
    payload = {"a": ["AKIAIOSFODNN7EXAMPLE"], "b": {"k": "ghp_" + "a" * 36}}
    redacted = redact_json(payload)
    assert "AKIAIOSFODNN7EXAMPLE" not in str(redacted)
    assert redacted["b"]["k"].startswith("[REDACTED:")
