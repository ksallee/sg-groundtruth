# Theme proposal

A replacement for `site/src/lib/tokens.css`, with the diagnosis it answers. Nothing in this document has
been applied. Screenshots were taken at 1440px and 390px, light and dark, against `npm run dev` with the
operator's overlay present, so every row and mark the three reading levels draw was on screen.

## Rules taken from the sibling project

`~/dev/css-fun-experiments` states its design rules in its own `DESIGN.md` and `docs/roles/DESIGNER.md`, neither of them here. Which ones
bind here:

| rule | applied |
|---|---|
| Neutrals at chroma 0, so the meaning colours are the only hues on a page | yes, unchanged |
| One meaning per colour, and meaning never rests on hue alone | yes, the three provenance accents and nothing else |
| Two states of one sentence get contrast ratios matched inside 6% | yes, the three accents now sit inside 1% in both schemes |
| Dark is drawn dark, never the light palette dimmed or inverted | yes, the dark ground rises and the dark slab falls |
| Square. Nothing in the shell is rounded | yes, all three radii to 0 |
| No shadow, gradient, glow or texture in the shell | yes, none added |
| One text face, one monospace for anything measured | yes, a serif for prose and a mono for every literal |
| Density is chosen once and held | yes, and it becomes two tokens rather than a value in two components |
| Every gap is one step of the spacing scale | yes, and three hardcoded lengths get named |
| Answer first, at the largest type, before any control | already true on every route |
| A 190px sticky rail of measured facts | no. That project's pages carry per-engine support data; these carry prose |
| `size-adjust` metric-matched webfont subsets | no. This site ships no font pipeline and this proposal adds none |
| The freeform demonstration region | no. Every region here is corpus markdown |

## Diagnosis

### Everywhere

| what | measured |
|---|---|
| The text face is `ui-sans-serif` | The hero at 56px is Helvetica Neue on the probed machine and Segoe UI on Windows. The site's largest element has no design decision in it |
| The mono face is `ui-monospace` | It resolves to SF Mono here, Cascadia there, DejaVu Sans Mono elsewhere. The face that sets every API literal, the wordmark and every label is the one the theme controls least |
| `--text-base` 15px and `--text-md` 17px | A 1.13 ratio. A list row's name and its verdict differ by 2px, so `EntryList` reads as one undifferentiated block |
| `--ground` 0.985 and `--ground-raised` 1.0 | 1.5% apart in light. The raised surface is invisible |
| Dark `--ground-sunken` 0.14 and `--slab` 0.12 | `#090909` against `#060606`. The code slab is not the darkest surface in dark, it is the same surface |
| `--wide` 78rem against `--measure` 64ch | A 1248px shell holding a 600px column. At 1440px, 690px of every prose page is empty |
| Two table densities | `Prose.svelte` cells pad `--space-2 --space-3` for a 37px row; `filters/+page.svelte` pads `--space-3` for a 46px row. Two tables on one site at two densities |
| Three hardcoded lengths | `border-left: 3px` in `EntryDetail.svelte` and `filters/+page.svelte`, `border-top: 2px` in `routes/+page.svelte`. `site/README.md` claims nothing hardcodes a length |

### `/`

The hero holds. `--text-display` at 56px, a 64ch lede, two actions. The reading order is correct and size
agrees with it.

Below it, `WHAT IT IS` at `--text-xs` mono uppercase muted, then the band headline at `--text-xl`. The
five facts are three columns with 2px top rules. The `Two corpora` heading is `--text-md`, its body is
`--text-sm` muted, and the two are 17px and 13px of the same face and the same colour family.

At 390px the sticky header stacks to three rows and stands 120px tall, which is 14% of the viewport, held
on every scroll.

### `/reference`

The whole page is 500px tall inside a 900px viewport, so the footer arrives with a band of empty ground
above it. Three columns of body text under 1px rules, and the group names (`Field types`, `Entity types`,
`Filters`) are set at `--text-md`, the same step as a fact heading on the landing page and a row name in a
list. The index over the site's three complete groups is the least distinguished page on the site.

### `/field-types` and `/findings`

One row is a mono name at 17px, a verdict at 15px muted, a tag row at 12px mono muted. Rows are 160px
tall and 600px wide inside a 1288px content width. Nothing sits in the right 45% at any level.

On `/findings` the number (`001`, `002`) is `--text-sm` muted beside a `--text-md` name, which is the one
place on the site where a hierarchy is drawn correctly.

### `/field-types/multi_entity`

The worst page for two reasons, both real.

| what | measured |
|---|---|
| Inline code | `background` plus `border` plus `radius`, on prose that is 40 to 60% API literals. The first body paragraph renders as 23 bordered boxes with connective words between them |
| The corpus's own section marks | `**Data type**`, `**Read**`, `**Write**`, `**Clear**` render as `font-weight: 650` inside the paragraph. The card's structure is invisible |
| A clipped table | The `[{"id": A}]` row's `matches` cell is cut mid-token at the container edge. `.scroll-x` scrolls it, and nothing on screen says so |
| The verdict rail | 3px solid `--accent`, which is the API scope edge drawn by hand rather than by `--scope-api-edge` |

### `/filters`

The densest page, 19129px tall at 1440px, and the hierarchy is inverted on it.

| element | set at |
|---|---|
| `h2` `Values, by data type` | `--text-lg`, 22px |
| `h3` `duration`, the name of the thing the section is about | `--text-xs`, 12px, uppercase, muted |
| `th` `OPERATOR` | `--text-xs`, 12px, uppercase, muted |
| `td` the data | `--text-sm`, 13px |

The name of the data type is the smallest text in its own section and is drawn identically to the column
head beneath it. A reader scrolling for `duration` has nothing larger than the body text to scan for.

The value matrix rows are 46px for cells holding `480` and `1`. Twenty-two such rows for `duration`, and
every row carries a full-width hairline, so five consecutive `is` rows read as five unrelated bands.

In the family tables the first column takes 450 to 750px to hold one word, because `table { width: 100% }`
with no column sizing spreads a two-column table across the shell. The column widths differ family to
family, so the operator chips start at a different x in every table on the page.

### `/recipes` and `/how-it-works`

Both work. `/how-it-works` is the only page where the slab, the prose and the headings sit at three clearly
different weights, because its headings are real `h2`s at `--text-lg` rather than mono labels.

## The theme

### Type

A serif sets prose and a monospace sets everything measured. The corpus is a record of what an API answered,
and the two registers are already there in the content: a sentence a person wrote, and a string the API
returned. One face each states it.

No webfont. `Charter` ships on macOS and iOS, `Sitka Text` and `Cambria` on Windows, `Georgia` everywhere
else, and the generic `serif` covers Linux and Android. This is a token-only change, needs no licence, adds
no request and no `@font-face`.

The named upgrade, if the operator later wants one render everywhere: **Source Serif 4** and **IBM Plex
Mono**, both OFL 1.1, both self-hostable as woff2. That change is two lines in `tokens.css` plus an
`@font-face` block, and it is listed under component changes because the block cannot live in `tokens.css`.

Seven steps. The ratio between `--text-base` and `--text-md` widens from 1.13 to 1.19 so a row name and its
verdict separate.

| token | rem | px | sets |
|---|---|---|---|
| `--text-xs` | 0.75 | 12 | tags, table heads, mono labels, the run-in section marks |
| `--text-sm` | 0.875 | 14 | table cells, notes, footer |
| `--text-base` | 1 | 16 | body prose |
| `--text-md` | 1.1875 | 19 | ledes, list-row names, verdicts, the data-type head on `/filters` |
| `--text-lg` | 1.5 | 24 | part heads |
| `--text-xl` | clamp | 28 to 40 | page `h1` |
| `--text-display` | clamp | 40 to 68 | the hero, one per site |

Four leadings, up from two. `--leading-snug` and `--leading-tabular` exist because heads and table cells
both wrap and neither wants 1.62.

| token | value | sets |
|---|---|---|
| `--leading-tight` | 1.12 | `h1` to `h4` |
| `--leading-snug` | 1.35 | ledes, verdicts, list rows |
| `--leading-normal` | 1.62 | body prose |
| `--leading-tabular` | 1.45 | table cells |

Measure moves from 64ch to 68ch. Charter's `0` is narrower than the sans it replaces, so 64ch of it lost
15px of column.

### Space

Eight steps, unchanged in the first five. Steps 6 to 8 grow, because the band separation on `/` and
`/reference` is one hairline and the type above it got larger.

| step | was | is | where |
|---|---|---|---|
| 1 | 4px | 4px | inside a row |
| 2 | 8px | 8px | label to sentence |
| 3 | 12px | 12px | header gaps, chip padding |
| 4 | 16px | 16px | slab padding, list-row padding |
| 5 | 24px | 24px | between blocks |
| 6 | 36px | 40px | between sections, page top padding |
| 7 | 56px | 64px | band padding, page bottom |
| 8 | 88px | 104px | the hero |

### Density

Two new tokens and one leading. A table row is `2 × --cell-y + --leading-tabular × --text-sm`, so
14 + 20.3 = 34px against 46px on `/filters` and 37px in `Prose`. The two tables agree for the first time,
and the number is one line to change.

| token | value |
|---|---|
| `--cell-y` | 0.4375rem |
| `--cell-x` | 0.75rem |
| `--leading-tabular` | 1.45 |

### Colour

Neutrals stay at chroma 0. The three provenance accents stay the only hues on a page, at the same three
hue angles, so the mark keeps the colours a reader has already learned.

Four changes:

| what | why |
|---|---|
| Light `--ground-sunken` 0.955 to 0.945 | The sunken surface was 3% off the ground and read as nothing |
| Dark `--ground` 0.17 to 0.235 | `#0f0f0f` left the slab nowhere to go. `#1e1e1e` gives the slab, the sunken ground and the raised ground four distinct steps |
| Dark `--slab` 0.12 to 0.155 | Follows the ground up, and stays the darkest surface by a visible step |
| The three accents retuned to matched contrast | Light 6.37, 6.39, 6.43. Dark 9.44, 9.39, 9.36. No level reads as louder than another |

Light and dark come from one `light-dark()` per colour, unchanged. No toggle, no script.

**Contrast, every ink-on-ground pair.** WCAG 2.1 ratios, computed from the oklch values below.

| pair | light | dark |
|---|---|---|
| `--ink` on `--ground` | 16.34 | 13.98 |
| `--ink` on `--ground-raised` | 17.31 | 12.04 |
| `--ink` on `--ground-sunken` | 14.74 | 15.34 |
| `--ink-muted` on `--ground` | 6.31 | 6.72 |
| `--ink-muted` on `--ground-sunken` | 5.69 | 7.37 |
| `--accent` on `--ground` | 6.37 | 9.44 |
| `--accent-local` on `--ground` | 6.39 | 9.39 |
| `--accent-project` on `--ground` | 6.43 | 9.36 |
| `--accent` on `--accent-quiet` | 5.92 | 7.72 |
| `--accent-local` on `--accent-local-quiet` | 6.10 | 7.47 |
| `--accent-project` on `--accent-project-quiet` | 6.04 | 7.53 |
| `--ink` on `--accent-quiet` | 15.20 | 11.43 |
| `--ink` on `--accent-local-quiet` | 15.60 | 11.13 |
| `--ink` on `--accent-project-quiet` | 15.35 | 11.25 |
| `--ink-muted` on `--accent-quiet` | 5.87 | 5.49 |
| `--ink-muted` on `--accent-local-quiet` | 6.02 | 5.35 |
| `--ink-muted` on `--accent-project-quiet` | 5.92 | 5.41 |
| `--slab-ink` on `--slab` | 14.42 | 14.50 |

Every pair clears AA at 4.5:1. Every pair except the muted ones clears AAA at 7:1. `--rule` and
`--rule-strong` are 1.33 and 2.03 in light, 1.53 and 2.55 in dark, and carry no meaning that is not also
carried by a word: they are hairlines, not state.

**The greyscale check.** The three accents resolve to `#5b5b5b`, `#5b5b5b` and `#5b5b5b` in light, and
`#c3c3c3`, `#c2c2c2` and `#c2c2c2` in dark. Nobody can separate them, which is what matching their ratios
means. The word (`The API`, `This site`, the project's name) and the edge texture (solid, dashed, dotted)
are the whole distinction, and neither moves in this proposal.

### Shape

Every radius to 0. A squared inset panel behind a textured left edge reads as a document's margin note; a
4px one reads as a card. The three token names stay, so rounding the site is still one line.

Three border widths, each with a meaning:

| token | value | draws |
|---|---|---|
| `--border` | 1px | every hairline and rule |
| `--border-bar` | 2px | the top rule over a card in a grid |
| `--scope-edge-width` | 3px | every provenance edge, and the verdict rail, which is the API edge |

## The replacement `tokens.css`

Complete and ready to apply. Each changed line carries why.

```css
/* ===========================================================================
   DESIGN SURFACE. Every colour, spacing step, font stack, radius and duration
   on the site is declared here. Change the look by changing this file; no
   component hardcodes a value.

   Light and dark come from one declaration each, via light-dark(). The page
   follows prefers-color-scheme and ships no theme script and no toggle.
   =========================================================================== */

:root {
	color-scheme: light dark;

	/* --- colour ----------------------------------------------------------
	   Neutrals sit at zero chroma so the accents are the only hues on the
	   page. Three accents exist, one per level of truth: --accent is a link
	   or a shipped fact, --accent-local marks content measured on one site,
	   --accent-project marks content measured on one project inside it.
	   Meaning never rests on colour alone; each band is also labelled and
	   boxed.

	   The three are tuned to the same contrast on the ground, 6.4 in light
	   and 9.4 in dark, so no level reads as louder than another. They
	   therefore resolve to one grey in greyscale. The word and the edge
	   texture below are the signals that carry. */
	--ground: light-dark(oklch(0.98 0 0), oklch(0.235 0 0));

	/* CHANGED. Dark was 0.17, which is #0f0f0f and left the slab nowhere
	   below it. At 0.235 the four dark surfaces are four visible steps. */
	--ground-raised: light-dark(oklch(1 0 0), oklch(0.285 0 0));

	/* CHANGED. Light was 0.955, 3% off the ground and invisible. */
	--ground-sunken: light-dark(oklch(0.945 0 0), oklch(0.195 0 0));

	--ink: light-dark(oklch(0.22 0 0), oklch(0.94 0 0));
	--ink-muted: light-dark(oklch(0.475 0 0), oklch(0.72 0 0));

	--rule: light-dark(oklch(0.885 0 0), oklch(0.36 0 0));
	--rule-strong: light-dark(oklch(0.76 0 0), oklch(0.48 0 0));

	/* CHANGED. Retuned from 0.45/0.78 to sit at 6.37 and 9.44 against the
	   ground, matching the two accents below inside 1%. */
	--accent: light-dark(oklch(0.475 0.17 255), oklch(0.825 0.13 255));
	--accent-quiet: light-dark(oklch(0.955 0.022 255), oklch(0.3 0.045 255));

	/* Site-specific content. Warm against the cool accent, so a reader can
	   tell a measurement from a rule at a glance. 6.39 and 9.39. */
	--accent-local: light-dark(oklch(0.48 0.13 62), oklch(0.82 0.12 72));
	--accent-local-quiet: light-dark(oklch(0.965 0.025 70), oklch(0.31 0.04 62));

	/* Project-specific content, one level narrower again. A third hue, so the
	   three levels of truth are three colours. Every band that uses it is also
	   labelled and boxed, so nothing rests on the hue alone. 6.43 and 9.36. */
	--accent-project: light-dark(oklch(0.458 0.11 155), oklch(0.8 0.12 155));
	--accent-project-quiet: light-dark(oklch(0.955 0.03 158), oklch(0.3 0.04 155));

	/* --- provenance ------------------------------------------------------
	   Three kinds of information share every list and every entry page, and
	   these nine lines are the whole distinction between them. Restyle it
	   here and it changes on the switch, on a list row, on a chip and on a
	   detail section at once.

	   A mark is three signals at once: a word, an edge texture and a hue.
	   The texture is the one that survives greyscale, a monochrome printout
	   and a reader who cannot separate the hues. Solid for the API, dashed
	   for one site, dotted for one project: coarser as the claim narrows.

	   UNCHANGED. The nine lines below are the load-bearing part of the
	   design and this proposal does not touch them. */
	--scope-api-ink: var(--accent);
	--scope-api-quiet: var(--accent-quiet);
	--scope-api-edge: linear-gradient(var(--accent), var(--accent));

	--scope-site-ink: var(--accent-local);
	--scope-site-quiet: var(--accent-local-quiet);
	--scope-site-edge: repeating-linear-gradient(
		var(--accent-local) 0 7px,
		transparent 7px 12px
	);

	--scope-project-ink: var(--accent-project);
	--scope-project-quiet: var(--accent-project-quiet);
	--scope-project-edge: repeating-linear-gradient(
		var(--accent-project) 0 2px,
		transparent 2px 6px
	);

	/* The width of every edge mark, so a chip and a section agree. The
	   verdict rail on an entry page is the same bar and reads this too. */
	--scope-edge-width: 3px;

	/* Code slabs are the darkest surface in both schemes, so quoted API
	   payloads read as one object at any brightness.
	   CHANGED. Dark was 0.12 against a 0.14 sunken ground, a 2% step that
	   was not a step. It follows the ground up and keeps its distance. */
	--slab: light-dark(oklch(0.21 0 0), oklch(0.155 0 0));
	--slab-ink: light-dark(oklch(0.93 0 0), oklch(0.9 0 0));

	/* --- type ------------------------------------------------------------
	   CHANGED. A serif sets prose, a monospace sets everything the API said.
	   The two registers are already in the content and the two faces state
	   it. No webfont: Charter ships on macOS and iOS, Sitka Text and Cambria
	   on Windows, Georgia elsewhere, generic serif on Linux and Android.

	   Swapping in Source Serif 4 and IBM Plex Mono, both OFL 1.1, is these
	   two lines plus an @font-face block, which cannot live in this file. */
	--font-text: Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif;
	--font-mono: ui-monospace, 'SF Mono', 'Cascadia Mono', 'Segoe UI Mono', 'Roboto Mono', Menlo,
		Consolas, monospace;

	/* CHANGED. Seven steps. --text-base to --text-md widens from 1.13 to
	   1.19, because a list row's name and its verdict were 2px apart and
	   read as one block. */
	--text-xs: 0.75rem;
	--text-sm: 0.875rem;
	--text-base: 1rem;
	--text-md: 1.1875rem;
	--text-lg: 1.5rem;
	--text-xl: clamp(1.75rem, 1.15rem + 2.4vw, 2.5rem);
	--text-display: clamp(2.5rem, 1.5rem + 4.6vw, 4.25rem);

	/* CHANGED. Four, up from two. Heads and table cells both wrap and
	   neither wants 1.62. */
	--leading-tight: 1.12;
	--leading-snug: 1.35;
	--leading-normal: 1.62;
	--leading-tabular: 1.45;

	/* --- space -----------------------------------------------------------
	   One scale, used for every margin, padding and gap.
	   CHANGED. Steps 1 to 5 hold. 6, 7 and 8 grow, because a band on / and
	   /reference is separated by one hairline and the type above it is now
	   larger. */
	--space-1: 0.25rem;
	--space-2: 0.5rem;
	--space-3: 0.75rem;
	--space-4: 1rem;
	--space-5: 1.5rem;
	--space-6: 2.5rem;
	--space-7: 4rem;
	--space-8: 6.5rem;

	/* --- density ---------------------------------------------------------
	   NEW. A table row is 2 * --cell-y + --leading-tabular * --text-sm, so
	   34px. It was 46px on /filters and 37px in Prose, two densities on one
	   site. Table density is one line here rather than a value in two
	   components. */
	--cell-y: 0.4375rem;
	--cell-x: 0.75rem;

	/* --- shape -----------------------------------------------------------
	   CHANGED. Square. An inset panel behind a textured left edge reads as a
	   margin note at 0 and as a card at 4px. The three names stay, so
	   rounding the site is still one line. */
	--radius-sm: 0px;
	--radius: 0px;
	--radius-lg: 0px;

	/* NEW. --border-bar names the 2px top rule over a card in a grid, which
	   routes/+page.svelte hardcodes today. */
	--border: 1px;
	--border-bar: 2px;

	/* --- measure ---------------------------------------------------------
	   Three widths. --measure is the reading column. --measure-wide is what a
	   reference table or a payload slab may spill out to before it starts
	   scrolling inside itself. --wide is the page shell.

	   The first two are capped at 100% because they are wider than a 390px
	   phone: without the cap a reference card widens the page instead of
	   scrolling inside its own container.

	   CHANGED. --measure 64ch to 68ch, because Charter's 0 is narrower than
	   the sans it replaces and 64ch of it lost 15px of column. --wide 78rem
	   to 72rem, because a 1248px shell held a 600px column and left 690px of
	   every prose page empty at 1440px. */
	--measure: min(100%, 68ch);
	--measure-wide: min(100%, 60rem);
	--wide: 72rem;
	--gutter: clamp(var(--space-4), 4vw, var(--space-6));

	/* The single column every stacked layout on the site declares. A grid's
	   default `auto` track is sized by its widest child's max-content, so one
	   long table cell widens the whole page and the percentages above have
	   nothing definite to resolve against. Stated here, used everywhere. */
	--col: minmax(0, 1fr);

	--duration: 120ms;
}

@media (prefers-reduced-motion: reduce) {
	:root {
		--duration: 0ms;
	}
}
```

## Per screen

Checked by injecting the block above, plus the five component rules listed below, into the running site
and rephotographing at 1440px in both schemes.

| screen | what the theme does |
|---|---|
| `/` | The hero is a 68px serif over a mono wordmark and mono nav, so the page states its two registers in the first 200px. The fact headings move to 19px against 16px body and separate. The band padding at 64px carries the larger type |
| `/reference` | Three group names at 19px serif over 16px descriptions, under 2px `--border-bar` rules. The page is still short; its emptiness is a layout question, not a token one |
| `/field-types` | The row name is 19px mono, the verdict 16px serif, the tags 12px mono. Three sizes, three faces, one row. The list scans |
| `/field-types/<slug>` | The bordered code chips lose their border and keep a tint, so a paragraph that is half literals reads as a paragraph. The run-in section marks (`Data type`, `Read`, `Write`, `Clear`) become 12px mono uppercase and the card's structure is visible for the first time |
| `/filters` | The data-type head goes from 12px uppercase muted to 19px mono ink, so it is larger than the table under it. Rows drop from 46px to 34px, which removes about 5,000px from the page. The clipped `matches` cell fades at the container edge instead of being cut mid-token |
| `/findings` | Unchanged in structure. The number stays `--text-sm` muted beside a now-19px name, so the pair separates further |
| `/recipes` | Same as `/findings` |
| `/how-it-works` | The slab is a step darker in dark and the headings move to 24px, so the three levels of the page hold at both brightnesses |
| The mark, at every level | Unchanged. Word, edge texture and hue, with the three hues now at matched contrast |

## What needs a component change

Five entries. Four are one line each. Everything else in this proposal lands from `tokens.css` alone.

| # | file | change | why a token cannot do it |
|---|---|---|---|
| 1 | `site/src/lib/components/Prose.svelte`, `site/src/routes/filters/+page.svelte` | `th`/`td` padding reads `var(--cell-y) var(--cell-x)` and `line-height: var(--leading-tabular)` | Both files name `var(--space-3)` today. Density is a decision made once, and it cannot be one until one token holds it |
| 2 | `site/src/lib/components/Prose.svelte`, `site/src/routes/filters/+page.svelte` | The section head (`Prose` `h2`, `filters` `h3`) reads `--text-md` in `--ink`, not `--text-xs` uppercase muted. In `Prose`, add `p > strong:first-child` styled as a run-in mono label | Both name `var(--text-xs)` explicitly. Raising `--text-xs` would also raise every tag, chip and table head. The run-in rule needs a selector, not a value. This also settles "the corpus marks its sections with bold" in `site/README.md` |
| 3 | `site/src/app.css` | `.scroll-x` gains a right-edge `mask-image` fade | A cell clipped mid-token with no affordance is a reader who does not know there is more. `.scroll-x` is already in `app.css` and the fade width can read `--space-6` |
| 4 | `site/src/lib/components/SiteHeader.svelte` | Below 640px, the bar is not sticky, or the reading level shares a row with the nav | 120px of sticky chrome on an 844px phone is 14% of the viewport, held on every scroll. Height comes from wrapping, not from a length |
| 5 | `site/src/lib/components/EntryDetail.svelte`, `site/src/routes/filters/+page.svelte`, `site/src/routes/+page.svelte` | The three hardcoded `3px`/`2px` bars read `var(--scope-edge-width)` and `var(--border-bar)` | `site/README.md` says nothing hardcodes a length. Three files do. The verdict rail is the API scope edge and should be drawn by the same token |

Entry 6, if the operator later wants one render on every platform: an `@font-face` block for Source Serif 4
and IBM Plex Mono, in `app.css` or a `fonts.css` beside it, with woff2 in `static/`. Both are OFL 1.1.
`--font-text` and `--font-mono` stay the only lines that name a face.

## Not proposed

| what | why not |
|---|---|
| A sticky rail or a two-column entry page, to use the 400px of empty width | It is the right answer to the emptiest screens and it is a layout rewrite of `EntryDetail`, `EntryList` and four routes. It is a separate piece of work with its own review |
| Column sizing on the `/filters` family tables | The 450px first column is real. Fixing it is a `<colgroup>` or a `grid` table in one route, and this run's stated goal is that the look changes from `tokens.css` |
| A tinted neutral, one hue for the product | `--accent-local` sits at hue 62. A warm neutral would put the Site mark on a ground of its own hue and cost the mark a signal |
| Syntax highlighting | `site/README.md` leaves it undecided for reasons this proposal does not change |
| A theme toggle | One `light-dark()` per colour, no script. Unchanged |

---

## As applied

The block above was applied on 2026-09-02. What shipped differs from what was proposed, and the
difference is recorded here rather than by editing the proposal, so the two stay separable.

| proposed | shipped | why |
|---|---|---|
| `--font-text` Charter, a serif | the system sans stack it replaced | Operator call: too loud against pages that are 40 to 60% literals |
| `--measure` 68ch | 64ch | 68ch existed to compensate for Charter's narrower `0`. The face went back, so the measure did |
| `.scroll-x` gains a right-edge `mask-image` | `background-attachment` covers and cues | The proposed mask faded unconditionally, including when the container had nothing to scroll, and its two reset selectors matched nothing |
| no token for either | `--scroll-cue` and `--surface` added | The cue needs a colour, and the covers need to know what they sit on. An inset local section has its own ground, so `ScopeSection` reassigns `--surface` |
| three hardcoded lengths named | five | `how-it-works/+page.svelte` held two more, a `3px` rail and a `2px` card rule |

### Claims checked before applying

Every one of the 36 contrast ratios is exact to two decimal places, computed from the oklch values.
No pair falls below AA. The three accents resolve to `#5b5b5b` in light and `#c2c2c2` in dark, so the
greyscale collapse the proposal claims is real.

One claim was wrong. `/filters` went from 19129px to 16112px at 1440px, which is 3017px removed, not the
"about 5,000px" the proposal states.

### Measured after applying

| | |
|---|---|
| table row, `/filters` and `Prose` | 35px, from 46 and 37 |
| `/filters` page height at 1440px | 16112px |
| data-type head on `/filters` | 19px ink, from 12px uppercase muted |
| `.scroll-x` on `/field-types/multi_entity` | 3 of 5 scroll; the 2 that do not draw no cue |
