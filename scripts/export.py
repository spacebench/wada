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
5. `boxes`: measure instead of rasterize — report the geometry of each
   slide's content boxes (figure slots, footer, columns) so figure authors
   read real slot dimensions rather than deriving them from CSS.

Artifacts are written to `.qa/` (gitignored). The output directory is
created if missing but NEVER deleted or cleared — the agent manages
artifacts itself, so A/B comparison runs can coexist via `--prefix`.

Usage
=====
    uv run python scripts/export.py png
    uv run python scripts/export.py pdf
    uv run python scripts/export.py png --input layouts/cover.html --prefix cover-
    uv run python scripts/export.py pdf --dir .qa/v2 --prefix A-
    uv run python scripts/export.py boxes
    uv run python scripts/export.py boxes --select ".figure,.notes" --json .qa/boxes.json

Run `uv run python scripts/export.py <subcommand> --help` for full flags.

One-time setup (see AGENTS.md §8)
---------------------------------
    uv add playwright
    uv run playwright install chromium-headless-shell

Parameters
----------
--input PATH   HTML file to render (default: deck.html). May point at a
               layout preview in layouts/*.html — those are standalone
               pages built from the same `.slide` markup. Accepted by all
               three subcommands.
--dir DIR      Output directory (default: .qa). Created if missing; never
               deleted/cleared — manage artifacts yourself. `png`/`pdf`.
--prefix STR   Filename prefix for namespacing runs, e.g. A/B comparisons
               (default: empty). Include your own separator: `--prefix A-`
               yields `A-slide-01.png` and `A-deck.pdf`. `png`/`pdf`.
--select SEL   `boxes` only: comma-separated CSS selectors to measure,
               replacing the default list.
--json PATH    `boxes` only: also write the measurements as JSON.

Subcommands
-----------
png  One PNG screenshot per `.slide` element → {dir}/{prefix}slide-NN.png
     (NN is zero-padded to the slide count's width). Exits non-zero if no
     `.slide` elements are found.
pdf  One print-exact PDF (one 1280×720 page per slide) → {dir}/{prefix}deck.pdf
boxes
     Read-only geometry report: per slide, the rect of every matched selector
     relative to the slide box, plus the post-`object-fit` content box for
     `.figure img`. WARNs when a `.slide-footer` rect overlaps a `.figure`.
     Writes nothing unless `--json PATH` is given.
"""

from __future__ import annotations

import argparse
import json
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


DEFAULT_BOX_SELECTORS = (
    ".figure",
    ".figure img",
    ".slide-footer",
    ".diagram-wrap",
    ".notes",
    ".body",
    ".cols",
    ".stats",
)

_MEASURE_JS = r"""
(selectors) => {
  const round = (n) => Math.round(n * 10) / 10;
  return Array.from(document.querySelectorAll('.slide')).map((slide, i) => {
    const sr = slide.getBoundingClientRect();
    const items = [];
    for (const sel of selectors) {
      for (const el of slide.querySelectorAll(sel)) {
        const r = el.getBoundingClientRect();
        const item = {
          selector: sel,
          tag: el.tagName.toLowerCase(),
          x: round(r.left - sr.left),
          y: round(r.top - sr.top),
          w: round(r.width),
          h: round(r.height),
        };
        const nw = el.naturalWidth, nh = el.naturalHeight;
        if (nw && nh && r.width && r.height) {
          const fit = getComputedStyle(el).objectFit;
          let scale = null;
          if (fit === 'contain') scale = Math.min(r.width / nw, r.height / nh);
          else if (fit === 'cover') scale = Math.max(r.width / nw, r.height / nh);
          if (scale !== null) {
            const cw = nw * scale, ch = nh * scale;
            item.content = {
              fit: fit,
              natural_w: nw,
              natural_h: nh,
              scale: Math.round(scale * 1000) / 1000,
              w: round(cw),
              h: round(ch),
              margin_x: round((r.width - cw) / 2),
              margin_y: round((r.height - ch) / 2),
            };
          }
        }
        items.push(item);
      }
    }
    return {
      index: i + 1,
      classes: slide.className,
      slide: { w: round(sr.width), h: round(sr.height) },
      items: items,
    };
  });
}
"""


def _overlap(a: dict, b: dict) -> bool:
    """True when two slide-relative rects intersect (zero-area edges excluded)."""
    return (
        a["x"] < b["x"] + b["w"]
        and b["x"] < a["x"] + a["w"]
        and a["y"] < b["y"] + b["h"]
        and b["y"] < a["y"] + a["h"]
    )


def cmd_boxes(args: argparse.Namespace) -> int:
    """Subcommand `boxes`: read-only geometry report, one section per slide."""
    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"export.py: input not found: {input_path}", file=sys.stderr)
        return 2

    if args.select:
        selectors = [s.strip() for s in args.select.split(",") if s.strip()]
    else:
        selectors = list(DEFAULT_BOX_SELECTORS)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        page.goto(_file_uri(input_path))
        _wait_ready(page)
        slides = page.evaluate(_MEASURE_JS, selectors)
        browser.close()

    if not slides:
        print(
            f"export.py: no '{SLIDE_SELECTOR}' elements found in {input_path}",
            file=sys.stderr,
        )
        return 3

    warnings: list[str] = []
    for slide in slides:
        print(f"\nslide {slide['index']:>2}  [{slide['classes']}]  "
              f"{slide['slide']['w']:g}×{slide['slide']['h']:g}")
        if not slide["items"]:
            print("  (no matched selectors)")
        for it in slide["items"]:
            print(
                f"  {it['selector']:<16} x={it['x']:>7.1f} y={it['y']:>7.1f} "
                f"w={it['w']:>7.1f} h={it['h']:>7.1f}"
            )
            c = it.get("content")
            if c:
                print(
                    f"  {'└ content':<16} w={c['w']:>7.1f} h={c['h']:>7.1f} "
                    f"({c['fit']}, natural {c['natural_w']}×{c['natural_h']}, "
                    f"scale {c['scale']:g}, margins {c['margin_x']:g}/{c['margin_y']:g})"
                )

        figures = [i for i in slide["items"] if i["selector"] == ".figure"]
        footers = [i for i in slide["items"] if i["selector"] == ".slide-footer"]
        for f in footers:
            if any(_overlap(f, fig) for fig in figures):
                msg = (
                    f"WARN slide {slide['index']}: .slide-footer overlaps .figure "
                    f"— keep the bottom ~56px of the figure corners empty "
                    f"(AGENTS.md §6)."
                )
                warnings.append(msg)
                slide.setdefault("warnings", []).append(msg)
                break

    if warnings:
        print()
        for msg in warnings:
            print(msg)

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {"input": str(input_path), "selectors": selectors, "slides": slides},
                indent=2,
            )
            + "\n"
        )
        print(f"\nboxes: wrote {out}")

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

    boxes = sub.add_parser(
        "boxes",
        help="Read-only geometry report: slot rects per slide (no files written).",
    )
    boxes.add_argument(
        "--input",
        default="deck.html",
        help="HTML file to measure (default: deck.html).",
    )
    boxes.add_argument(
        "--select",
        default="",
        help=(
            "Comma-separated CSS selectors to measure, replacing the default "
            f"list ({', '.join(DEFAULT_BOX_SELECTORS)})."
        ),
    )
    boxes.add_argument(
        "--json",
        default="",
        help="Also write the measurements as JSON to this path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "png":
        return cmd_png(args)
    if args.command == "pdf":
        return cmd_pdf(args)
    if args.command == "boxes":
        return cmd_boxes(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
