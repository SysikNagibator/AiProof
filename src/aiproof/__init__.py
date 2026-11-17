"""AiProof by SYSIK: the agent says done. AiProof checks the receipts."""

from __future__ import annotations

__all__ = ["__author__", "__version__", "version_string"]

__version__ = "0.1.1"
__author__ = "SYSIK"


def version_string() -> str:
    """Return the canonical version banner, e.g. ``AiProof 0.1.0 by SYSIK``."""
    return f"AiProof {__version__} by {__author__}"
