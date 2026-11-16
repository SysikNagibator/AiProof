#!/usr/bin/env python3
"""Print i18n catalog completeness per language.

Usage: ``python tools/gen_catalog_report.py [--strict]``.
``--strict`` exits non-zero when English or Russian is incomplete (CI gate);
draft catalogs are reported but never fail the build.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aiproof.i18n import KNOWN_LANGS, SOURCE_LANG, _load, available, is_reviewed  # noqa: E402

PLACEHOLDER = re.compile(r"\{(\w+)\}")


def main(argv: list[str]) -> int:
    """Print the report; return a process exit code."""
    strict = "--strict" in argv
    english = _load(SOURCE_LANG)
    print(f"source: {SOURCE_LANG} ({len(english)} keys)\n")
    print(f"{'lang':<8}{'keys':>6}{'missing':>9}{'extra':>7}{'placeholders':>14}  reviewed")
    print("-" * 58)
    failures: list[str] = []
    for code in KNOWN_LANGS:
        if code not in available():
            print(f"{code:<8}{'-':>6}{'-':>9}{'-':>7}{'-':>14}  missing catalog")
            if code in ("en", "ru"):
                failures.append(code)
            continue
        catalog = _load(code)
        missing = sorted(set(english) - set(catalog))
        extra = sorted(set(catalog) - set(english))
        mismatched = [
            key
            for key in english
            if key in catalog
            and set(PLACEHOLDER.findall(english[key])) != set(PLACEHOLDER.findall(catalog[key]))
        ]
        reviewed = "yes" if is_reviewed(code) else "machine"
        print(
            f"{code:<8}{len(catalog):>6}{len(missing):>9}{len(extra):>7}"
            f"{len(mismatched):>14}  {reviewed}"
        )
        if code in (SOURCE_LANG, "ru") and (missing or mismatched):
            failures.append(code)
    if failures:
        print(f"\nincomplete required catalog(s): {', '.join(sorted(set(failures)))}")
        return 1 if strict else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
