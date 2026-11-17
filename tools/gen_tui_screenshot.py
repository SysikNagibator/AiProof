#!/usr/bin/env python3
"""Render the AiProof TUI to ``docs/assets/tui.svg`` (and PNG when Chrome is available).

The image is produced from the *real* renderer (:mod:`aiproof.tui.app`), not drawn by
hand, so the README screenshot always matches the shipped UI. Run it after changing the
TUI and commit the regenerated assets::

    python tools/gen_tui_screenshot.py
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
WIDTH = 100
HEIGHT = 466  # px, tuned to the rendered frame


def _render_svg() -> str:
    from rich.console import Console

    from aiproof import paths
    from aiproof.config import Settings
    from aiproof.tui import app

    os.environ.setdefault("AIPROOF_LANG", "en")
    root = paths.project_root()
    state = app.State(lang="en", theme_name="green")
    console = Console(
        record=True, width=WIDTH, force_terminal=True, color_system="truecolor", file=io.StringIO()
    )
    console.print(app._build(root, Settings(), state))
    return console.export_svg(title="AiProof TUI")


def _rasterize(svg_path: Path) -> Path | None:
    """Turn the SVG into a PNG with headless Chrome/Chromium, when present."""
    chrome = (
        shutil.which("google-chrome")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )
    if not chrome:
        return None
    png_path = svg_path.with_suffix(".png")
    subprocess.run(
        [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            f"--window-size={WIDTH * 12 + 40},{HEIGHT}",
            f"--screenshot={png_path}",
            f"file://{svg_path}",
        ],
        check=False,
        capture_output=True,
    )
    return png_path if png_path.is_file() and png_path.stat().st_size > 0 else None


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    svg_path = ASSETS / "tui.svg"
    svg_path.write_text(_render_svg(), encoding="utf-8")
    print(f"wrote {svg_path.relative_to(ROOT)}")
    png = _rasterize(svg_path)
    if png is not None:
        print(f"wrote {png.relative_to(ROOT)}")
    else:
        print("note: no Chrome/Chromium found; PNG not regenerated (SVG is up to date)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
