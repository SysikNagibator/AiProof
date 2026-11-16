"""Known secret formats as data (each pattern has positive/negative tests).

Each entry carries the *type* label used in reports, a compiled regex, and the
capture-group index that holds the secret to replace (0 = whole match).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Pattern:
    """A labelled secret pattern."""

    type: str
    regex: re.Pattern[str]
    group: int = 0


def _p(type_: str, pattern: str, group: int = 0, flags: int = 0) -> Pattern:
    return Pattern(type_, re.compile(pattern, flags), group)


SECRET_PATTERNS: tuple[Pattern, ...] = (
    _p("aws_access_key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    _p(
        "aws_secret_key",
        r"(?i)aws_?secret_?access_?key['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})",
        1,
    ),
    _p("github_token", r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
    _p("github_pat", r"\bgithub_pat_[A-Za-z0-9_]{22,255}\b"),
    _p("gitlab_token", r"\bglpat-[A-Za-z0-9_\-]{20,}\b"),
    _p("slack_token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    _p("stripe_key", r"\b(?:sk|pk|rk)_(?:live|test)_[0-9A-Za-z]{16,}\b"),
    _p("twilio_key", r"\bSK[0-9a-fA-F]{32}\b"),
    _p("sendgrid_key", r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}\b"),
    _p("openai_key", r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{20,}\b"),
    _p("anthropic_key", r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"),
    _p("google_api_key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    _p("npm_token", r"\bnpm_[A-Za-z0-9]{36}\b"),
    _p("pypi_token", r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_\-]{20,}\b"),
    _p("jwt", r"\beyJ[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{4,}\b"),
    _p(
        "private_key_block",
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----[\s\S]+?-----END "
        r"(?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
    ),
    _p(
        "db_url",
        r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|amqps?|rediss)://"
        r"[^\s:@/]+:[^\s@/]+@[^\s]+",
    ),
    _p("bearer_token", r"(?i)\bBearer\s+([A-Za-z0-9\-._~+/]{12,}={0,2})", 1),
    _p("authorization_header", r"(?i)\bAuthorization:\s*([^\r\n]+)", 1),
    _p(
        "assigned_secret",
        r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)"
        r"['\"]?\s*[:=]\s*['\"]?([^\s'\"#;,]{8,})",
        1,
    ),
    _p("npmrc_token", r"(?m)^\s*//[^\s]+:_authToken\s*=\s*(\S+)", 1),
    _p("pypirc_password", r"(?im)^\s*password\s*=\s*(\S+)", 1),
)

# Variable names that hint a nearby high-entropy token is a secret.
SENSITIVE_HINT = re.compile(
    r"(?i)\b(key|token|secret|passwd|password|pwd|credential|auth|private|apikey)\b"
)

# Token candidate for the entropy pass.
ENTROPY_CANDIDATE = re.compile(r"[A-Za-z0-9+/_\-]{20,}")

# Things that are long/high-entropy but NOT secrets.
BENIGN_LOOKALIKES: tuple[re.Pattern[str], ...] = (
    re.compile(r"^[0-9a-fA-F]{40}$"),  # git sha1
    re.compile(r"^[0-9a-fA-F]{64}$"),  # sha256
    re.compile(r"^[0-9a-fA-F]{7,40}$"),  # abbreviated sha
    re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$"),  # uuid
    re.compile(r"^\d+$"),  # numeric id
    re.compile(r"^\d+\.\d+\.\d+"),  # semver-ish
    re.compile(r"^(?:sha256|sha512|md5)-[A-Za-z0-9+/=]{20,}$"),  # lockfile integrity
)
