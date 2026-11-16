"""All filesystem locations used by AiProof, cross-platform.

Design notes:
* Every path is derived here, never hard-coded elsewhere.
* Windows specifics handled: ``normcase`` folds case, long paths assumed enabled
  on Python 3.11+; we never build ``\\\\?\\`` manually.
* The project key is the SHA-256 of the *canonical* git top-level path (or cwd
  when not a git repo), truncated to 16 hex chars for readable directory names;
  the full digest is stored in ``project.json`` for integrity.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

APP_DIRNAME = ".aiproof"
ENV_PREFIX = "AIPROOF_"
PROJECT_JSON = "project.json"
LEDGER_FILE = "ledger.jsonl"
PINNED_FILE = "pinned.toml"
RECEIPTS_DIR = "receipts"
ALLOW_FILE = "allow.toml"
RULES_FILE = "rules.toml"
LOG_FILE = "aiproof.log"
KEY_FILE = "key"
GLOBAL_CONFIG = "config.toml"

_HASH_LEN = 16


def home_dir() -> Path:
    """Return the AiProof home directory (``~`` unless overridden)."""
    override = os.environ.get(f"{ENV_PREFIX}HOME")
    if override:
        return Path(override).expanduser()
    return Path.home()


def data_dir() -> Path:
    """Return the AiProof data directory (``~/.aiproof`` by default)."""
    override = os.environ.get(f"{ENV_PREFIX}DATA_DIR")
    if override:
        return Path(override).expanduser()
    return home_dir() / APP_DIRNAME


def global_config_path() -> Path:
    """Return the user-level config file path."""
    return data_dir() / GLOBAL_CONFIG


def key_path() -> Path:
    """Return the optional ledger HMAC key path (0600 when created)."""
    return data_dir() / KEY_FILE


def log_path() -> Path:
    """Return AiProof's own operational log path (separate from the ledger)."""
    return data_dir() / LOG_FILE


def is_disabled() -> bool:
    """Return True when the emergency kill switch ``AIPROOF_DISABLE=1`` is set."""
    return os.environ.get(f"{ENV_PREFIX}DISABLE", "").strip() in {"1", "true", "yes"}


def canonical_path(path: Path) -> Path:
    """Return a canonical, symlink-resolved, case-normalized absolute path."""
    resolved = Path(os.path.realpath(os.path.abspath(os.fspath(path))))
    normal = os.path.normcase(os.fspath(resolved))
    return Path(normal)


def git_toplevel(cwd: Path) -> Path | None:
    """Return the git top-level for *cwd*, or ``None`` when not in a git repo."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.fspath(cwd),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return Path(out) if out else None


def project_root(cwd: Path | None = None) -> Path:
    """Return the canonical project root (git top-level, else *cwd*)."""
    base = canonical_path(cwd if cwd is not None else Path.cwd())
    top = git_toplevel(base)
    if top is not None:
        return canonical_path(top)
    return base


def project_hash(root: Path) -> str:
    """Return the full SHA-256 hex digest of a project root's canonical path."""
    canonical = os.fspath(canonical_path(root))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def projects_dir() -> Path:
    """Return the directory that holds every per-project store."""
    return data_dir() / "projects"


def project_dir(root: Path) -> Path:
    """Return the per-project data directory (created lazily by callers)."""
    return projects_dir() / project_hash(root)[:_HASH_LEN]


def ledger_path(root: Path) -> Path:
    """Return the ledger JSONL path for a project."""
    return project_dir(root) / LEDGER_FILE


def pinned_path(root: Path) -> Path:
    """Return the pinned-settings path for a project."""
    return project_dir(root) / PINNED_FILE


def receipts_dir(root: Path) -> Path:
    """Return the receipts directory for a project."""
    return project_dir(root) / RECEIPTS_DIR


def project_meta_path(root: Path) -> Path:
    """Return the ``project.json`` alias/meta path for a project."""
    return project_dir(root) / PROJECT_JSON


def project_allow_path(root: Path) -> Path:
    """Return the in-repo secrets allowlist path (``.aiproof/allow.toml``)."""
    return root / APP_DIRNAME / ALLOW_FILE


def rules_path(root: Path) -> Path:
    """Return the compiled-rules store path for a project."""
    return project_dir(root) / RULES_FILE


def repo_config_path(root: Path) -> Path:
    """Return the in-repo advisory config path (``aiproof.toml``)."""
    return root / "aiproof.toml"
