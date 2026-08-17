#!/usr/bin/env python3
"""
export.py — QA export tooling for the slide deck.

Purpose
=======
Replaces the raw system-chromium CLI previously used for QA. Renders
`deck.html` (or any standalone HTML page, e.g. a layout preview in
`layouts/`) to PNG screenshots — one per slide — and to a print-exact PDF,
using Playwright's chromium-headless-shell.

The deck is static HTML + CSS with no JavaScript. One `.slide` element
equals one PDF page (via CSS `@page { size: 1280px 720px }` +
`break-after: page`). This script preserves that invariant: the PDF page
count equals the `.slide` count, and each PNG is a 1280×720 capture of a
single `.slide` element.

How it works
============
1. Launch chromium-headless-shell (Playwright's default headless browser —
   no `channel` argument is passed, so the full Chromium download is
   skipped and only the headless shell is used).
2. Open the target HTML via a `file://` URI at a 1280×720 viewport.
3. Wait for `networkidle` AND `document.fonts.ready` so Google Fonts and
   other webfonts are fully loaded before capture — otherwise captures
   can show fallback metrics.
4. `png`:  locate every `.slide` element and screenshot each one to its
   own file. `pdf`: call `page.pdf(print_background=True,
   prefer_css_page_size=True)` so the CSS `@page` size (1280×720) and
   `break-after: page` rules produce one page per slide, identical to the
   screen rendering.

Artifacts are written to `.qa/` (gitignored). The output directory is
created if missing but NEVER deleted or cleared — the agent manages
artifacts itself, so A/B comparison runs can coexist via `--prefix`.

Usage
=====
    uv run python scripts/export.py png
    uv run python scripts/export.py pdf
    uv run python scripts/export.py png --input layouts/cover.html --prefix cover-
    uv run python scripts/export.py pdf --dir .qa/v2 --prefix A-

Run `uv run python scripts/export.py <subcommand> --help` for full flags.

One-time setup (see AGENTS.md §8)
---------------------------------
    uv add playwright
    uv run playwright install chromium-headless-shell

Parameters (common to both subcommands)
---------------------------------------
--input PATH   HTML file to render (default: deck.html). May point at a
               layout preview in layouts/*.html — those are standalone
               pages built from the same `.slide` markup.
--dir DIR      Output directory (default: .qa). Created if missing; never
               deleted/cleared — manage artifacts yourself.
--prefix STR   Filename prefix for namespacing runs, e.g. A/B comparisons
               (default: empty). Include your own separator: `--prefix A-`
               yields `A-slide-01.png` and `A-deck.pdf`.

Subcommands
-----------
png  One PNG screenshot per `.slide` element → {dir}/{prefix}slide-NN.png
     (NN is zero-padded to the slide count's width). Exits non-zero if no
     `.slide` elements are found.
pdf  One print-exact PDF (one 1280×720 page per slide) → {dir}/{prefix}deck.pdf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import Page, sync_playwright

# Slide geometry — must match the CSS tokens --slide-w / --slide-h in
# styles/base.css. Kept here as plain ints so the viewport matches the
# print page exactly for pixel-identical PNG vs PDF rendering.
SLIDE_W = 1280
SLIDE_H = 720

# Every slide in the deck (and every layout preview) is a
# <section class="slide ...">. Screenshots and page breaks key off this.
SLIDE_SELECTOR = ".slide"


def _file_uri(path: Path) -> str:
    """Return a file:// URI for an absolute path (spaces/unicode-safe)."""
    return "file://" + quote(str(path))


def _wait_ready(page: Page) -> None:
    """Wait for network idle + webfonts so captures match screen rendering.

    `networkidle` covers Google Fonts requests settling; `document.fonts.ready`
    guarantees the FontFaceSet has finished loading before we rasterize.
    """
    page.wait_for_load_state("networkidle")
    page.evaluate("async () => { if (document.fonts) { await document.fonts.ready; } }")


def cmd_png(args: argparse.Namespace) -> int:
    """Subcommand `png`: one 1280×720 PNG per `.slide` element."""
    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"export.py: input not found: {input_path}", file=sys.stderr)
        return 2

    out_dir = Path(args.dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        page.goto(_file_uri(input_path))
        _wait_ready(page)

        slides = page.locator(SLIDE_SELECTOR).all()
        if not slides:
            print(
                f"export.py: no '{SLIDE_SELECTOR}' elements found in {input_path}",
                file=sys.stderr,
            )
            browser.close()
            return 3

        # Zero-pad slide numbers to the count's width (e.g. 6 slides → 01..06,
        # 42 slides → 01..42) so filenames sort lexicographically.
        width = max(2, len(str(len(slides))))
        for i, slide in enumerate(slides, start=1):
            name = f"{args.prefix}slide-{str(i).zfill(width)}.png"
            slide.screenshot(path=str(out_dir / name))
        browser.close()

    print(f"png: wrote {len(slides)} slide(s) to {out_dir}/")
    return 0


def cmd_pdf(args: argparse.Namespace) -> int:
    """Subcommand `pdf`: one print-exact PDF, one page per slide."""
    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"export.py: input not found: {input_path}", file=sys.stderr)
        return 2

    out_dir = Path(args.dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{args.prefix}deck.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        page.goto(_file_uri(input_path))
        _wait_ready(page)

        # print_background=True is required for colored surfaces to appear.
        # prefer_css_page_size=True makes the PDF honor `@page { size: 1280px
        # 720px }` from styles/base.css §1; combined with `break-after: page`
        # on each .slide this yields one 1280×720 page per slide. Margins are
        # zeroed to match `@page { margin: 0 }`.
        page.pdf(
            path=str(out_file),
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()

    print(f"pdf: wrote {out_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser with shared flags on both subcommands."""
    parser = argparse.ArgumentParser(
        prog="export.py",
        description=(
            "QA export for the slide deck: one PNG per slide and a "
            "print-exact PDF, via Playwright chromium-headless-shell."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--input",
            default="deck.html",
            help="HTML file to render (default: deck.html).",
        )
        p.add_argument(
            "--dir",
            default=".qa",
            help="Output directory, created if missing (default: .qa).",
        )
        p.add_argument(
            "--prefix",
            default="",
            help=(
                "Filename prefix for namespacing runs; include your own "
                "separator, e.g. --prefix A- (default: empty)."
            ),
        )

    add_common(sub.add_parser("png", help="One PNG screenshot per .slide."))
    add_common(sub.add_parser("pdf", help="Print-exact PDF, one page per slide."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "png":
        return cmd_png(args)
    if args.command == "pdf":
        return cmd_pdf(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
