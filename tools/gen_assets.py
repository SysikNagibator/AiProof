#!/usr/bin/env python3
"""Generate AiProof raster assets with **no external dependencies**.

This is the dependency-free complement to ``tools/build_icon.py`` (which prefers a real SVG
rasterizer). It draws the same design — a rounded dark-green tile with a shield check mark —
directly into PNG buffers using ``zlib`` + ``struct``, then assembles ``.ico`` and ``.icns``
containers and two banner PNGs. Deterministic and offline.

    python tools/gen_assets.py

Outputs under ``assets/``: ``AiProof_Logo_{16..1024}.png``, ``AiProof_Logo.png`` (1024),
``AiProof.ico``, ``AiProof.icns``, ``banner_en.png``, ``banner_ru.png``.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

RGB = tuple[int, int, int]

TILE_A: RGB = (7, 33, 15)
TILE_B: RGB = (11, 58, 28)
BORDER: RGB = (29, 92, 51)
MARK_A: RGB = (94, 240, 138)
MARK_B: RGB = (18, 161, 80)
CHECK: RGB = (138, 255, 171)

# Segments of the check mark in the 512-viewBox design space.
CHECK_SEGMENTS = ((196.0, 262.0, 238.0, 306.0), (238.0, 306.0, 322.0, 212.0))
CHECK_WIDTH = 30.0


def _lerp(a: RGB, b: RGB, t: float) -> tuple[float, float, float]:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _rounded_inside(
    x: float, y: float, x0: float, y0: float, x1: float, y1: float, r: float
) -> bool:
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    dx = x - cx
    dy = y - cy
    return dx * dx + dy * dy <= r * r


def _seg_dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx = bx - ax
    dy = by - ay
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return ((px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2) ** 0.5


def _sample(size: int, u: float, v: float) -> tuple[float, float, float, float]:
    """Return premultiplied RGBA for a design-space point (0..1)."""
    x = u * 512.0
    y = v * 512.0
    inset = 16.0
    radius = 104.0
    if not _rounded_inside(x, y, inset, inset, 512 - inset, 512 - inset, radius):
        return (0.0, 0.0, 0.0, 0.0)

    # background gradient (diagonal), plus an inner border band
    t = (u + v) / 2.0
    r, g, b = _lerp(TILE_A, TILE_B, t)
    border_w = 6.0
    if not _rounded_inside(
        x,
        y,
        inset + border_w,
        inset + border_w,
        512 - inset - border_w,
        512 - inset - border_w,
        radius - border_w,
    ):
        r, g, b = BORDER

    # check mark
    half = CHECK_WIDTH / 2.0
    for ax, ay, bx, by in CHECK_SEGMENTS:
        if _seg_dist(x, y, ax, ay, bx, by) <= half:
            r, g, b = _lerp(CHECK, MARK_A, y / 512.0)
            break

    return (float(r), float(g), float(b), 1.0)


def render_icon(size: int, ss: int) -> bytes:
    """Render the icon at *size* px with *ss* supersampling; return RGBA bytes."""
    buf = bytearray(size * size * 4)
    inv = 1.0 / (ss * ss)
    for py in range(size):
        for px in range(size):
            acc_r = acc_g = acc_b = acc_a = 0.0
            for sy in range(ss):
                vy = (py + (sy + 0.5) / ss) / size
                for sx in range(ss):
                    vx = (px + (sx + 0.5) / ss) / size
                    r, g, b, a = _sample(size, vx, vy)
                    acc_r += r * a
                    acc_g += g * a
                    acc_b += b * a
                    acc_a += a
            a = acc_a * inv
            idx = (py * size + px) * 4
            if a <= 0.0:
                continue
            buf[idx] = int(min(255, acc_r * inv / a))
            buf[idx + 1] = int(min(255, acc_g * inv / a))
            buf[idx + 2] = int(min(255, acc_b * inv / a))
            buf[idx + 3] = int(min(255, a * 255))
    return bytes(buf)


# --- tiny 5x7 font for the banner wordmark -----------------------------------------------
_FONT: dict[str, tuple[str, ...]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    " ": ("00000",) * 7,
}


def _draw_text(
    buf: bytearray, width: int, height: int, text: str, x0: int, y0: int, scale: int, color: RGB
) -> None:
    cursor = x0
    for char in text.upper():
        glyph = _FONT.get(char)
        if glyph is None:
            cursor += 4 * scale
            continue
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit != "1":
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        px = cursor + gx * scale + dx
                        py = y0 + gy * scale + dy
                        if 0 <= px < width and 0 <= py < height:
                            idx = (py * width + px) * 4
                            buf[idx], buf[idx + 1], buf[idx + 2], buf[idx + 3] = (
                                color[0],
                                color[1],
                                color[2],
                                255,
                            )
        cursor += (5 + 1) * scale


def render_banner(width: int, height: int, tag: str) -> bytes:
    """Render a dark banner with the AIPROOF wordmark and a language tag."""
    buf = bytearray(width * height * 4)
    radius = height / 3.0
    for py in range(height):
        for px in range(width):
            if not _rounded_inside(px + 0.5, py + 0.5, 2, 2, width - 2, height - 2, radius):
                continue
            t = py / height
            r, g, b = _lerp(TILE_A, TILE_B, t)
            if not _rounded_inside(px + 0.5, py + 0.5, 5, 5, width - 5, height - 5, radius - 3):
                r, g, b = BORDER
            idx = (py * width + px) * 4
            buf[idx], buf[idx + 1], buf[idx + 2], buf[idx + 3] = int(r), int(g), int(b), 255

    scale = max(4, height // 9)
    text_w = len("AIPROOF") * 6 * scale - scale
    _draw_text(
        buf, width, height, "AIPROOF", (width - text_w) // 2, int(height * 0.22), scale, CHECK
    )
    sub = max(2, height // 22)
    sub_text = f"BY SYSIK - {tag}"
    sub_w = len(sub_text) * 6 * sub - sub
    _draw_text(buf, width, height, sub_text, (width - sub_w) // 2, int(height * 0.66), sub, MARK_A)
    return bytes(buf)


def write_png(path: Path, width: int, height: int, rgba: bytes) -> None:
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw += rgba[y * stride : (y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(data)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def build_ico(path: Path, pngs: list[tuple[int, bytes]]) -> None:
    count = len(pngs)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    entries = bytearray()
    payload = bytearray()
    for size, data in pngs:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        payload += data
        offset += len(data)
    path.write_bytes(header + bytes(entries) + bytes(payload))


def build_icns(path: Path, members: list[tuple[bytes, bytes]]) -> None:
    body = bytearray()
    for type_code, data in members:
        body += type_code + struct.pack(">I", len(data) + 8) + data
    total = 8 + len(body)
    path.write_bytes(b"icns" + struct.pack(">I", total) + bytes(body))


def _supersample(size: int) -> int:
    if size <= 128:
        return 4
    if size <= 512:
        return 2
    return 1


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    pngs: dict[int, bytes] = {}
    for size in (16, 32, 48, 64, 128, 256, 512, 1024):
        data = render_icon(size, _supersample(size))
        pngs[size] = data
        write_png(ASSETS / f"AiProof_Logo_{size}.png", size, size, data)
    # canonical large logo
    write_png(ASSETS / "AiProof_Logo.png", 1024, 1024, pngs[1024])

    build_ico(ASSETS / "AiProof.ico", [(s, pngs[s]) for s in (16, 32, 48, 64, 128, 256)])
    build_icns(
        ASSETS / "AiProof.icns",
        [
            (b"ic07", pngs[128]),
            (b"ic08", pngs[256]),
            (b"ic09", pngs[512]),
        ],
    )

    write_png(ASSETS / "banner_en.png", 960, 200, render_banner(960, 200, "EN"))
    write_png(ASSETS / "banner_ru.png", 960, 200, render_banner(960, 200, "RU"))
    print("generated:", ", ".join(sorted(p.name for p in ASSETS.iterdir())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
