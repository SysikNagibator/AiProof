"""Explicit-consent self-update with SHA-256 verification (no silent updates)."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from aiproof import __version__

RELEASES_API = "https://api.github.com/repos/SYSIK/aiproof/releases/latest"
TIMEOUT = 10


@dataclass(slots=True)
class UpdateInfo:
    """Information about an available release."""

    current: str
    latest: str
    newer: bool
    changelog: str = ""
    url: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        """Return True when the release check actually succeeded."""
        return not self.error


def _parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in value.lstrip("v").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check() -> UpdateInfo:
    """Check GitHub releases (network). Never installs anything."""
    failure = "could not reach the release API"
    try:
        req = urllib.request.Request(RELEASES_API, headers={"User-Agent": "aiproof"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            data: Any = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return UpdateInfo(__version__, __version__, False, error=f"{failure}: {exc}")
    if not isinstance(data, dict):
        return UpdateInfo(
            __version__, __version__, False, error="release API returned invalid JSON"
        )
    latest = str(data.get("tag_name", __version__))
    return UpdateInfo(
        current=__version__,
        latest=latest,
        newer=_parse_version(latest) > _parse_version(__version__),
        changelog=str(data.get("body", ""))[:4000],
        url=str(data.get("html_url", "")),
    )


def verify_sha256(path: str, expected: str) -> bool:
    """Return True when *path*'s SHA-256 matches *expected* (from the manifest)."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest().lower() == expected.strip().lower()
