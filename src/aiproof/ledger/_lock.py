"""Cross-platform advisory file lock (best effort)."""

from __future__ import annotations

import contextlib
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

try:  # POSIX
    import fcntl

    _HAVE_FCNTL = True
except ModuleNotFoundError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]
    _HAVE_FCNTL = False

try:  # Windows
    import msvcrt

    _HAVE_MSVCRT = True
except ModuleNotFoundError:  # pragma: no cover - POSIX
    msvcrt = None  # type: ignore[assignment]
    _HAVE_MSVCRT = False


@contextlib.contextmanager
def file_lock(path: Path, timeout: float = 5.0) -> Iterator[None]:
    """Acquire an exclusive advisory lock on a sidecar lock file.

    This is best-effort: on exotic platforms without either backend the lock is
    a no-op (single-writer operation still holds by design for the ledger).

    Raises :class:`TimeoutError` when the lock cannot be acquired within
    *timeout* — the caller must never proceed unlocked.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = os.open(os.fspath(path), os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + timeout
    acquired = False
    try:
        while not acquired:
            try:
                if _HAVE_FCNTL and fcntl is not None:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                elif _HAVE_MSVCRT and msvcrt is not None:  # pragma: no cover - Windows
                    win = cast("Any", msvcrt)
                    win.locking(handle, win.LK_NBLCK, 1)
                acquired = True
            except OSError as exc:
                if time.monotonic() >= deadline:
                    # Never enter the critical section without the lock: doing so
                    # silently forks the ledger chain. Fail loudly instead; hooks
                    # treat it as an internal error and fail open.
                    raise TimeoutError(f"could not acquire lock: {path}") from exc
                time.sleep(0.02)
        yield
    finally:
        if acquired:
            with contextlib.suppress(OSError):
                if _HAVE_FCNTL and fcntl is not None:
                    fcntl.flock(handle, fcntl.LOCK_UN)
                elif _HAVE_MSVCRT and msvcrt is not None:  # pragma: no cover
                    win = cast("Any", msvcrt)
                    win.locking(handle, win.LK_UNLCK, 1)
        os.close(handle)
