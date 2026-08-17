# AGENTS.md — Slide Deck Harness

You are a slide-deck builder. One repo clone, one finished deck: `deck.html`. The deck is the product itself, edited directly with the user in a ping-pong workflow — a deck, not a template. Print to PDF must reproduce the screen exactly, one `.slide` per page.

The whole system is static HTML + CSS + SVG. Its palette sensibility is inspired by Sanzo Wada's *A Dictionary of Color Combinations* — each theme is a small, named palette in that spirit.

## 1. Non-negotiables

- **Print-exactness.** One `.slide` = one PDF page, pixel-identical to screen. The `@page` / print rules in `styles/base.css` §1 and the slide geometry tokens (`--slide-w`, `--slide-h`) are load-bearing — leave them alone.
- **Tokens, not hex.** Colors and fonts reach HTML and `base.css` only through `var(--…)`. Hex values live in theme files and inside standalone `.svg` figures (§6). This is what makes a deck re-themeable by swapping one `<link>`.
- **Slides fit.** A slide that overflows is rewritten or split. Verify visually (§8) before calling it done.

## 2. Repository

```
deck.html                ← the deck (the only file we edit content in)
styles/
  tokens.css             ← theme contract: every color/font token a theme must define. Reference only — never link it.
  base.css               ← structural tokens (type scale, spacing, geometry, radii) + all structural CSS + print rules + the 16 layout classes.
  themes/
    kujaku.css           ← main theme: teal + purple
    sumi.css             ← dark ink + persimmon / gold
    kinari.css           ← warm paper + rust / indigo
layouts/                 ← 16 standalone-previewable slide markup snippets
assets/                  ← standalone .svg figures + svg-template.svg
scripts/export.py        ← Playwright renderer for QA (§8)
```

## 3. Tokens

Two layers, owned by two files:

- **Theme tokens** — colors and font stacks. The contract (which token names every theme must define) lives in `styles/tokens.css`; the values live in each `styles/themes/*.css`. Use semantic names (`--accent-secondary`, not "purple"); for any text-on-color choice, follow the active theme's approved contrast pairings (documented in its header).
- **Structural tokens** — type scale, weights, leading, tracking, spacing, slide geometry, radii, shadows. Owned by `styles/base.css` §2. Themes leave these alone — geometry especially, for print fidelity.

## 4. Themes

The active theme is one line in `deck.html`:

```html
<link rel="stylesheet" href="styles/themes/kujaku.css">
```

Swap that line and the whole deck re-themes. Each theme file imports its Google Fonts, defines every contract token, and carries a header with: the **SVG style block** to paste into figures (§6), the **approved contrast pairings**, and a Wada-inspired provenance note (say honestly when values are hand-tuned approximations).

To add a palette: create `styles/themes/<name>.css` following the existing files (font import, header with SVG style block + contrast pairs, all tokens), then switch the link. Keep palettes in the spirit of Wada's dictionary.

## 5. Layouts — composing slides

Each file in `layouts/` is a copy-paste `<section>` snippet, standalone-previewable, with content limits documented in its header. To add a slide: copy the snippet into `deck.html`, fill the slots. All layout CSS lives in `base.css`.

| Layout | Use for |
|---|---|
| `cover` | Title, subtitle, author/date. |
| `section-divider` | Numbered break between major parts. |
| `agenda` | Table of contents / progress marker (`.active`). |
| `title-bullets` | Default content slide. ≤5 bullets, ≤14 words each. |
| `two-column` | Text‖text or text‖figure, balanced columns. |
| `three-cards` | 2–4 parallel items (`.cards-2/-4` variants). |
| `big-statement` | The one sentence to remember. ≤20 words. Rare. |
| `stat-grid` | 2–4 headline KPIs. |
| `quote` | One citation/testimonial. |
| `image-full` | Full-bleed visual + caption bar. |
| `image-split` | 50/50 figure + explanation (`.flip` variant). |
| `comparison` | A vs B (`.panel-featured` for the winner). |
| `process-steps` | 3–5 step pipeline/timeline. |
| `table` | ≤6 rows × ≤5 cols of comparable data. |
| `diagram-focus` | Big SVG diagram + ≤3 side notes. |
| `closing` | Final slide: thanks, ask, contact. |

The 16 layouts cover the common cases and should be used as-is ~99% of the time. They are a starting point — when a slide genuinely needs a small deviation to serve the user's instruction, deviate. The styling vocabulary (`.kicker`, `.lead`, `.cards-*`, `.figure`, the `inverse` modifier) is composable. Consecutive slides on the same layout read as a rut — vary them.

Global modifiers: any `<section class="slide …">` takes `inverse` (dark background via `--bg-inverse`). Optional `.slide-footer` shows deck title + page number — keep page numbers in sync.

## 6. SVG figures

Figures are standalone `.svg` files in `assets/`, embedded with `<img src="assets/<name>.svg">`. SVG markup lives in `assets/*.svg` — figures stay self-contained and openable in any SVG tool (browser, Chromium print, Illustrator, Inkscape).

Pattern, starting from `assets/svg-template.svg`:

1. The first child of `<svg>` is a `<style>` block copied **verbatim** from the active theme's header. It defines semantic classes (`accent-primary`, `stroke-strong`, …) with plain hex — that block is the theme copy, and plain hex is why figures render identically outside the browser.
2. Paint with those classes; add `fill="none"` on stroke-only elements.
3. To re-theme a figure, replace its `<style>` block with another theme's.
4. In-figure text uses `font-family="sans-serif"` / `serif` / `monospace` — locally available fonts. `<img>`-embedded SVGs cannot fetch webfonts, so theme font names do not work inside figures.
5. `viewBox` always; fixed `width`/`height` never. Keep `role="img"` + `aria-label`. Figures scale inside `.figure` (`.figure-contain` = letterboxed, default = cropped cover).

The figure canvas defaults to transparent so the slide background shows through — the right default ~99% of the time. The theme's `--bg-*` classes are available inside figures for opaque shapes (cards, panels, badges) or, when a figure needs it, a full background. Choose deliberately: a stray full-bleed rect produces a visible "white box" over the slide.

In HTML, figure slots are marked with a `.figure-ph` placeholder — replace with the `<img>` when the figure exists.

## 7. Content

Slides are spoken support, not a document. Short sentences, one idea per slide. The title states the takeaway, not the topic ("Model beats baseline by 25 points", not "Results"). Prefer a figure or a number over a paragraph. When in doubt, split the slide.

## 8. QA

Render with the uv-managed Playwright script — `scripts/export.py`.

First-time setup on a machine (browser binary cached in `~/.cache/ms-playwright/`, shared across clones):

```sh
uv run playwright install chromium-headless-shell
```

`uv.lock` pins Python deps; `uv run` auto-syncs the venv, so there is no separate sync step. From the repo root:

```sh
# One 1280×720 PNG per slide — visual overflow / clipping checks:
uv run python scripts/export.py png

# Print-exact PDF, one 1280×720 page per slide:
uv run python scripts/export.py pdf
```

Flags: `--input PATH` (default `deck.html`; can point at a `layouts/*.html` preview), `--dir DIR` (default `.qa`, gitignored), `--prefix STR` (namespace runs, e.g. `A-`). Both subcommands wait for `document.fonts.ready` so webfonts settle. `.qa/` is never auto-cleared — manage artifacts yourself. Full flags: `uv run python scripts/export.py png --help`.

Then **look at the PNGs** and inspect the PDF (page count = slide count, page size = 1280×720). Every slide must pass:

- text within the frame; figures not clipped; columns balanced
- layout content limits respected (bullets, words, rows)
- colors via tokens; no inline `<svg>` in any `.html`
- every figure's first child is the active theme's SVG style block; elements painted via its classes
- every SVG has `viewBox`, `role` / `aria-label`, no fixed `width`/`height`
- text-on-color follows the theme's approved contrast pairings
- page numbers / footers consistent
- webfonts loaded (network available) before printing
