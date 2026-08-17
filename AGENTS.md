# AGENTS.md — Slide Deck Harness

You are assisting the user in building **one HTML slide deck** in this repo. The deck is `deck.html`. It is the final product, not a template — we edit it directly, together, in a ping-pong workflow. When printed to PDF, the deck must look exactly like the screen.

---

## 1. Goal & non-negotiable rules

- **One deck per repo clone.** All work happens in `deck.html`.
- **No JavaScript.** Ever. The deck is static HTML + CSS + SVG.
- **Print-exactness.** One `.slide` = one PDF page, identical to screen. Never break §1 of `styles/base.css` (the `@page` / print rules) and never change the slide geometry tokens (`--slide-w`, `--slide-h`).
- **Colors and fonts come only from design tokens** (`var(--…)`). Raw hex values are forbidden in every `.html` file and in `styles/base.css`. Hex lives only in theme files and inside standalone figure files (see §6).
- **Slides never overflow.** Content that doesn't fit is rewritten or split into two slides. Always verify visually (§8).

## 2. Repository structure

```
AGENTS.md                ← this file: your complete instructions
deck.html                ← THE deck (the only file we edit content in)
styles/
  tokens.css             ← THEME CONTRACT: every color/font token a theme must define. Reference only — never link it.
  base.css               ← owns the STRUCTURAL tokens (type scale, spacing, slide geometry, radii) + all structural CSS + print rules + the 16 layout classes.
  themes/
    kujaku.css           ← MAIN theme: teal + purple (biology/AI identity)
    sumi.css             ← dark ink + persimmon/gold
    kinari.css           ← warm paper + rust/indigo
layouts/                 ← 16 standalone-previewable slide markup snippets
assets/
  svg-template.svg       ← annotated starter for new figures
  pipeline.svg           ← example figure used by the seed deck
```

## 3. The token contract

Two kinds of tokens, owned by two different files:

- **Theme tokens** (the contract, `styles/tokens.css`): what every theme MUST define — colors and font stacks only:
  - Surfaces: `--bg-base`, `--bg-surface`, `--bg-muted`, `--bg-inverse`
  - Text: `--text-primary`, `--text-secondary`, `--text-inverse`, `--text-on-accent`
  - Accents: `--accent-primary` (signature), `--accent-secondary`, `--accent-tertiary`, `--accent-inverse` (accent on inverse surfaces)
  - Borders: `--border-subtle`, `--border-strong`
  - Fonts: `--font-display`, `--font-body`, `--font-mono`
- **Structural tokens** (owned by `styles/base.css` §2): type scale (`--text-xs`…`--text-display`), weights, leading, tracking, spacing (`--space-1..8`), slide geometry, radii, shadows. Themes don't touch them.

Rules: semantic tokens only (`--accent-secondary`, never "purple"); use spacing tokens instead of arbitrary px; respect each theme's **approved contrast pairings** (documented in its header) for all text-on-color choices.

## 4. Themes

- The active theme is chosen by **one line** in `deck.html`: `<link rel="stylesheet" href="styles/themes/kujaku.css">`
- To re-theme: change that one line. Nothing else in the deck changes.
- Each theme file imports its Google Fonts and defines every token of the contract, plus a header containing: the **SVG STYLE BLOCK** (ready to paste into figure files — see §6), the **approved contrast pairings**, and the palette's provenance note (Sanzo Wada-inspired; see file header).

If the user asks for a new palette: create `styles/themes/<name>.css` following the existing files exactly (font import, header with SVG style block + contrast pairs, all tokens), then switch the link. Prefer palettes in the spirit of Sanzo Wada's *A Dictionary of Color Combinations* and say so honestly when values are hand-tuned approximations.

## 5. Layouts — how to compose slides

Each file in `layouts/` is a **copy-paste markup snippet** (a standalone previewable page). To add a slide: copy its `<section>` into `deck.html`, fill the slots, respect its content limits (documented in the file header). All styling already lives in `base.css` — never write layout CSS in deck.html.

| Layout file | Use it for |
|---|---|
| `cover.html` | Slide 1. Title, subtitle, author/date. |
| `section-divider.html` | Numbered break between major parts. |
| `agenda.html` | Table of contents / progress marker (`.active`). |
| `title-bullets.html` | Default content slide. ≤5 bullets, ≤14 words each. |
| `two-column.html` | Text‖text or text‖figure, balanced columns. |
| `three-cards.html` | 2–4 parallel items (`.cards-2/-4` variants). |
| `big-statement.html` | The one sentence to remember. ≤20 words. Rare. |
| `stat-grid.html` | 2–4 headline KPIs. |
| `quote.html` | One citation/testimonial. |
| `image-full.html` | Full-bleed visual + caption bar. |
| `image-split.html` | 50/50 figure + explanation (`.flip` variant). |
| `comparison.html` | A vs B (`.panel-featured` for the winner). |
| `process-steps.html` | 3–5 step pipeline/timeline. |
| `table.html` | ≤6 rows × ≤5 cols of comparable data. |
| `diagram-focus.html` | Big SVG diagram + ≤3 side notes. |
| `closing.html` | Final slide: thanks, ask, contact. |

Global modifiers: any `<section class="slide …">` accepts `inverse` (dark background via `--bg-inverse`). Optional `.slide-footer` inside a slide shows deck title + page number — keep page numbers in sync.

**Vary the layouts.** Consecutive slides using the same layout are a smell; the outline step (§7) exists to catch that.

## 6. SVG figures

Figures are **always standalone `.svg` files in `assets/`**, embedded with `<img src="assets/<name>.svg">`. NEVER inline SVG markup into `deck.html` or layout copies — no exceptions.

Every figure file must be **self-contained and openable in any SVG tool** (browsers, Chromium print, Illustrator, Inkscape…). The pattern:

1. Start from `assets/svg-template.svg`.
2. The first child of `<svg>` is a `<style>` block copied **verbatim** from the active theme's header ("SVG STYLE BLOCK" in `styles/themes/<name>.css`). It defines semantic classes with **plain hex values** — never `var()`. This block IS the theme copy.
3. Paint elements with those classes (`class="accent-primary"`, `class="stroke-strong"`…), never with raw hex attributes. Add `fill="none"` on elements that only take a stroke.
4. To re-theme a figure: replace its `<style>` block with another theme's block. Nothing else in the file changes.
5. In-figure text: `font-family="sans-serif"` (or `serif`/`monospace`) — locally available fonts, renders anywhere. (`<img>`-embedded SVGs cannot fetch webfonts — do not reference theme font names inside figure files.)
6. `viewBox` always, fixed `width`/`height` never; keep `role="img"` + `aria-label`. Figures scale inside `.figure` containers (`.figure-contain` = letterboxed, default = cropped cover).

In HTML, figure slots are marked with a `.figure-ph` placeholder div — replace it with the `<img>` when the figure exists.

## 7. Workflow (the ping-pong)

1. **Ask** (if not yet known): topic, audience, talk length / slide count, tone — and propose a theme (default: `kujaku`).
2. **Propose an outline** before writing markup: a table of `slide # → layout → content in ≤10 words → SVG needed?`. Get the user's approval. This is where layout variety and narrative arc are fixed.
3. **Build** the deck in `deck.html` following the outline.
4. **Iterate** slide by slide with the user. Small, reviewable edits.
5. **QA** (§8) before declaring done, and after any structural change.

## 8. QA — mandatory before delivery

The agent renders QA artifacts with the uv-managed Playwright scripts in `scripts/` (see §9) — **not** system Chromium. The script is the agent's internal renderer.

First-time setup: the browser binary is machine-wide (cached in `~/.cache/ms-playwright/`, not per clone), so install it once per machine:

```sh
uv run playwright install chromium-headless-shell
```

Python deps are already pinned in `uv.lock`; `uv run` auto-syncs the venv on every invocation, so there is no separate sync step.

Then from the repo root:

```sh
# One PNG per slide (1280×720 each) for visual overflow/clipping checks:
uv run python scripts/export.py png

# Print-exact PDF (one 1280×720 page per slide):
uv run python scripts/export.py pdf
```

Both subcommands accept `--input PATH` (default `deck.html`; can point at a `layouts/*.html` preview), `--dir DIR` (default `.qa`, gitignored), and `--prefix STR` to namespace A/B runs without clobbering earlier artifacts. Full flags: `uv run python scripts/export.py png --help`. Artifacts land in `.qa/` and are never auto-deleted — manage them yourself.

Then **look at the PNGs** (and inspect the PDF: page count = slide count, page size = 1280×720). Check every slide for:

- [ ] no text overflow, no clipped figures, no unbalanced columns
- [ ] layout content limits respected (bullets, words, rows)
- [ ] no raw hex and no inline `<svg>` in any .html file
- [ ] every figure in assets/ carries the active theme's SVG STYLE BLOCK as its first child; elements painted via its classes only
- [ ] every SVG has viewBox, role/aria-label, no fixed width/height
- [ ] contrast pairs approved by the active theme
- [ ] page numbers / footers consistent
- [ ] fonts loaded (network available) before printing

## 9. Scripts

Standalone Python tools the agent uses for QA and rendering. All run via `uv run` against the project venv managed by uv; `uv.lock` pins versions for reproducibility.

| Script | Purpose |
|---|---|
| `scripts/export.py` | Render `deck.html` (or any `layouts/*.html` preview) to PNG screenshots and a print-exact PDF via Playwright chromium-headless-shell. |

### `scripts/export.py`

Two subcommands:

- `png` — one 1280×720 PNG per `.slide` element → `.qa/slide-NN.png` (for visual overflow/clipping checks).
- `pdf` — one print-exact PDF, one 1280×720 page per slide → `.qa/deck.pdf` (honors CSS `@page { size: 1280px 720px }` + `break-after: page`).

Common flags: `--input PATH` (default `deck.html`), `--dir DIR` (default `.qa`), `--prefix STR` (namespace runs; include your own separator, e.g. `A-`). Both subcommands wait for `document.fonts.ready` before capture so webfonts are settled.

First-time setup — the browser binary is machine-wide (cached in `~/.cache/ms-playwright/`, not per clone), so install it once per machine. Python deps are already pinned in `uv.lock`; `uv run` auto-syncs the venv, so no separate sync step is needed:

```sh
uv run playwright install chromium-headless-shell
```

Run from the repo root:

```sh
uv run python scripts/export.py png
uv run python scripts/export.py pdf
```

The script never deletes or clears `.qa/` — the agent manages artifacts itself.

## 10. Content guidance

Slides are spoken support, not a document. Short sentences. One idea per slide. The slide title states the takeaway, not the topic ("Model beats baseline by 25 points", not "Results"). Prefer a figure or a number over a paragraph. When in doubt, split the slide.
