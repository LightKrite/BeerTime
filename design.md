# Design — BeerTime

Locked design system for this app. Every template redesign reads this file
first; extend or amend it here rather than inventing a new system per page.

## Why this exists

The first version's cell showed a coloured emoji (the evening's verdict) and
was edited by tapping the cell to cycle through five states — the thing you
saw and the thing you edited were different, with no visible link. This
redesign makes the cell show the day's shift kind as a word; the background
colour carries the verdict. What you see is what you edit. The board stays
the point of the app — everything else (best-evenings strip, legend, forms)
is deliberately quieter than the grid.

## Genre

Custom — modern-minimal restraint (dashboard energy, laconic) carrying a
tuned warm-amber palette tied to the project's own subject. None of
Hallmark's 21 marketing macrostructures fit a live-edit shift grid, so the
board's structure is bespoke; the palette/type/motion discipline underneath
it is the same discipline any Hallmark build follows.

## Macrostructure family

One family — this app has no marketing pages, every route is the working
tool itself.

- **Board** (`/`) — bespoke: compact best-evenings strip (secondary, chip
  badges) → sticky-header data table (own row edits via native `<select>`,
  status colour on every cell) → chip lists of who's free / who's early
  tomorrow → legend. The grid is the hero; nothing above it fights for
  attention.
- **Forms** (`/me`, `/join`) — a single centred card, `max-width: 26rem`,
  labelled inputs stacked above their fields. No enrichment — these are
  utility forms, not marketing moments.

## Nav — N1a, by the stated exception

Wordmark (hand-drawn pint-glass mark + "BeerTime" in the display face) +
two links (`доска`, `мой график`). N1a is banned as a default elsewhere in
Hallmark's catalogue, but its own exception is explicit: reach for it when
the page genuinely has two destinations. This one does.

## Footer

None. A closing strip only — the colour legend plus one hint line. A
six-person utility tool has no sitemap, no legal page, no newsletter; a
marketing footer archetype here would be slop by the same logic that bans
the AI nav on a bakery site.

## Palette

Custom OKLCH, anchored on hue 55 (amber — a beer note, not a photo of one).
Every pairing below is a computed WCAG 2.1 ratio, not an eyeballed guess —
see § Contrast.

```css
--color-paper:    oklch(97% 0.014 60);   /* warm cream */
--color-paper-2:  oklch(94% 0.017 58);
--color-paper-3:  oklch(90% 0.020 58);

--color-ink:      oklch(21% 0.020 45);   /* warm near-black */
--color-ink-2:    oklch(40% 0.018 45);
--color-muted:    oklch(50% 0.015 50);

--color-rule:     oklch(58% 0.020 55);   /* real boundaries, 3.9:1 */
--color-rule-2:   oklch(84% 0.016 55);   /* decorative only */

--color-accent:      oklch(46% 0.17 55); /* the one amber note */
--color-accent-ink:  var(--color-paper);
--color-focus:       oklch(44% 0.21 55);

--color-green:   oklch(91% 0.05 145);
--color-yellow:  oklch(91% 0.06 85);
--color-red:     oklch(90% 0.06 25);
--color-blocked: oklch(89% 0.018 55);
```

Axes: **light / roman-serif / warm (amber ~55°)**.

**The status colours are a separate semantic set from the brand accent.**
Green/yellow/red/grey answer "can this person meet tonight?" — that
question existed before this redesign and is answered in `schedule.py`, not
by taste. The accent answers "what does BeerTime look like?" — reserved for
the focus ring, the wordmark mark, links, and the primary button fill. The
two systems never swap roles: a cell's meaning never depends on the brand
colour, and the brand colour never leaks into a cell.

## Contrast

Every colour pair actually used on the page, computed (not eyeballed) at
build time:

| Pair | Ratio |
| --- | --- |
| ink on paper | 16.3:1 |
| ink-2 on paper | 8.5:1 |
| muted on paper | 5.5:1 |
| ink on paper-2 | 14.9:1 |
| accent as text on paper | 6.9:1 |
| paper text on accent fill | 6.9:1 |
| focus ring on paper | 7.6:1 |
| ink on green/yellow/red/blocked backgrounds | 12.7–13.8:1 |
| rule (real boundary) on paper | 3.9:1 |

Two things this ruled out: **ink text on the accent fill is only 2.4:1** —
the primary button always uses paper-coloured text, never ink, on its
amber fill. And the focus ring's own hue matches the accent, so it would
vanish drawn directly over an accent-filled element — every focus ring
uses `outline-offset` so it draws against the surrounding page background
instead of overlapping the element's own fill.

## Typography

```css
--font-display: "Literata", Georgia, "Times New Roman", serif;
--font-body:    "Geist", ui-sans-serif, system-ui, -apple-system, sans-serif;
```

Two families, roman only — no italic headers anywhere. Display carries only
weight 600 (h1/h2, the wordmark); body runs 400/500/600.

**Why Literata and not Fraunces/Newsreader/Source Serif/Bricolage** — the
obvious warm-editorial serif choices — **is a hard constraint, not a
preference**: this app's entire UI is Russian, and none of those four ship
a Cyrillic subset on Google Fonts. Literata does (verified by fetching its
actual CSS2 response with a Cyrillic-glyph page, not by assumption), keeps
the same warm-reading-serif register, and has a real weight range. Any
future display-face swap on this project must re-verify Cyrillic coverage
the same way before adopting a face from Hallmark's own catalogue table —
that table is Latin-tested by default.

Both faces are **self-hosted** (`static/fonts/*.woff2`, Cyrillic + Latin
subsets only — this UI has no other scripts) rather than linked from
Google's CDN. The app previously made zero requests outside its own
origin; a `<link>` to fonts.googleapis.com would have quietly broken that
property (every visitor's browser leaking their IP/referrer to Google) for
a typography upgrade. Confirmed post-build: 11 requests on a cold load, all
same-origin.

## Spacing

4pt scale, named by role:

```css
--space-3xs: 0.25rem;  --space-2xs: 0.5rem;   --space-xs: 0.75rem;
--space-sm:  1rem;     --space-md:  1.5rem;   --space-lg: 2rem;
--space-xl:  3rem;     --space-2xl: 4.5rem;
```

## Radius

```css
--radius-sm:   8px;    /* cells, inputs, badges */
--radius-md:   14px;   /* the table card, form cards */
--radius-pill: 999px;  /* chips, buttons, badges */
```

## Motion

```css
--ease-out:    cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
--dur-fast:  120ms;
--dur-short: 200ms;
```

Exactly one orchestrated motion primitive on the whole app: `#board` fades
in via `@starting-style` when HTMX swaps it after an edit — a 200ms opacity
crossfade, so the eye registers that something changed. It degrades safely
in browsers without `@starting-style` support (renders at full opacity
immediately, no error) and collapses under `prefers-reduced-motion` along
with every other transition. Everything else — select/button hover,
focus rings — is baseline interaction-state styling, not an "entrance."

## Microinteractions stance

- Silent success: saving a schedule or flipping a cell just shows the new
  state. No toast for an action the user can already see worked.
- Focus rings never animate in — instant, per the global `:focus-visible`
  rule — and always sit on a reserved `outline: 2px solid transparent`
  slot so no element's border-box size changes between states.
- Inputs and the cell `<select>` follow the no-layout-shift discipline:
  border width is constant across default/hover/focus; state changes move
  to `background-color` and `outline` only.

## CTA voice

- Primary button (`.btn`): pill radius, solid `--color-accent` fill, paper
  text, 44px minimum height. One per form.
- Nav links and the wordmark carry no fill — colour and a soft background
  tint on hover/focus is enough for a two-destination nav.

## What pages must share

The wordmark mark and its amber colour · the accent's restriction to
focus/links/primary-button/mark (never a full-cell or full-section fill) ·
the display+body pairing · the 4pt spacing scale · the pill-button and
chip voice · the status-colour set being read-only outside `schedule.py`'s
own logic.

## What pages may differ on

Board vs. form-card is already the full range this app needs. A future
page would pick between those two shapes, not invent a third, unless the
app grows a genuinely new kind of screen.

## Per-page allowances

No page carries enrichment (hero art, illustration, generated imagery).
The board's one hand-drawn touch — a simple line-art pint glass, single
stroke, in the accent colour, ~22px in the header — is Tier A pure SVG,
not a generated or "AI-illustration-look" asset, and appears in exactly
one place (the wordmark). It is not repeated as a decorative motif
elsewhere on the page.
