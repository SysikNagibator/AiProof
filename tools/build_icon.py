#!/usr/bin/env python3
"""Generate AiProof icon assets from the SVG logo.

This script is *optional*: it needs an external SVG rasterizer. It prefers, in order:

1. ``cairosvg`` (pure Python + cairo)
2. ``rsvg-convert`` (librsvg CLI)
3. ``inkscape`` CLI
4. ImageMagick ``magick``/``convert``

If none is available it prints the exact manual steps and exits 0, so it never breaks a
build. The committed ``assets/AiProof_Logo.svg`` is the source of truth; the raster outputs
(``.png``, ``.ico``, ``.icns``) are generated artifacts.

Usage::

    python tools/build_icon.py [--force]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG = ASSETS / "AiProof_Logo.svg"

PNG_SIZES = (16, 32, 48, 64, 128, 256, 512, 1024)


def _run(cmd: list[str]) -> bool:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return False
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return False
    return True


def _rasterize_pngs() -> str | None:
    """Write PNGs and return the name of the tool used, or None."""
    if _has_module("cairosvg"):
        import cairosvg  # type: ignore[import-not-found]

        for size in PNG_SIZES:
            out = ASSETS / f"AiProof_Logo_{size}.png"
            cairosvg.svg2png(url=str(SVG), write_to=str(out), output_width=size, output_height=size)
        return "cairosvg"

    if shutil.which("rsvg-convert"):
        for size in PNG_SIZES:
            out = ASSETS / f"AiProof_Logo_{size}.png"
            if not _run(
                ["rsvg-convert", "-w", str(size), "-h", str(size), str(SVG), "-o", str(out)]
            ):
                return None
        return "rsvg-convert"

    if shutil.which("inkscape"):
        for size in PNG_SIZES:
            out = ASSETS / f"AiProof_Logo_{size}.png"
            if not _run(
                [
                    "inkscape",
                    str(SVG),
                    "--export-type=png",
                    f"--export-filename={out}",
                    f"--export-width={size}",
                    f"--export-height={size}",
                ]
            ):
                return None
        return "inkscape"

    magick = shutil.which("magick") or shutil.which("convert")
    if magick:
        for size in PNG_SIZES:
            out = ASSETS / f"AiProof_Logo_{size}.png"
            if not _run(
                [magick, "-background", "none", "-resize", f"{size}x{size}", str(SVG), str(out)]
            ):
                return None
        return magick

    return None


def _has_module(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


def _build_ico() -> bool:
    """Assemble AiProof.ico from the PNG set (needs Pillow)."""
    if not _has_module("PIL"):
        return False
    from PIL import Image  # type: ignore[import-not-found]

    source = ASSETS / "AiProof_Logo_256.png"
    if not source.is_file():
        return False
    image = Image.open(source)
    image.save(ASSETS / "AiProof.ico", sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
    return True


def _build_icns() -> bool:
    """Assemble AiProof.icns (macOS-only tooling)."""
    if sys.platform != "darwin" or not shutil.which("iconutil"):
        return False
    iconset = ASSETS / "AiProof.iconset"
    iconset.mkdir(exist_ok=True)
    mapping = {
        16: "16x16",
        32: "32x32",
        64: "64x64",
        128: "128x128",
        256: "256x256",
        512: "512x512",
    }
    for size, label in mapping.items():
        src = ASSETS / f"AiProof_Logo_{size}.png"
        if src.is_file():
            shutil.copy(src, iconset / f"icon_{label}.png")
            shutil.copy(src, iconset / f"icon_{label}@2x.png")
    return _run(["iconutil", "-c", "icns", str(iconset), "-o", str(ASSETS / "AiProof.icns")])


def main() -> int:
    if not SVG.is_file():
        print(f"missing source logo: {SVG}", file=sys.stderr)
        return 1
    tool = _rasterize_pngs()
    if tool is None:
        print(
            "No SVG rasterizer found. Install one of cairosvg, librsvg (rsvg-convert),\n"
            "inkscape or ImageMagick, then re-run. Manual fallback:\n"
            f"  rsvg-convert -w 1024 -h 1024 {SVG} -o {ASSETS}/AiProof_Logo_1024.png\n"
            "  (the .ico needs Pillow; the .icns needs macOS `iconutil`)\n"
            "The SVG is the committed source of truth; raster outputs are build artifacts."
        )
        return 0
    print(f"rasterized PNGs with {tool}")
    print("built .ico" if _build_ico() else "skipped .ico (Pillow not available)")
    print("built .icns" if _build_icns() else "skipped .icns (macOS iconutil not available)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
