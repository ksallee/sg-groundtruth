# The design process

How the look of `site/` gets changed, and how Paper and the running site are kept saying the same thing.

## What ships, and where it gets changed

`site/src/lib/tokens.css` is what ships. Every colour, length, face, radius and duration on the site is
one line in it, and no component hardcodes a value.

Paper tokens are CSS variables scoped to a Paper file, and every artboard in that file reads them. Change
one and every artboard updates. That makes Paper a real place to tweak the theme rather than a place to
illustrate it, which is the point of rebuilding the pages there: a token moves and you see it land on
every screen at once.

The round trip:

| step | how |
|---|---|
| `tokens.css` into Paper | once, via the MCP: point the agent at the file and have it create the tokens |
| tweak | in Paper's Theme tab. Every artboard reflects it |
| Paper back into `tokens.css` | Theme tab, select all, Copy, paste into `tokens.css` |
| what ships | the paste, reviewed, committed. Paper is never read by the build |

Paper writing the site directly stays disallowed. The canvas would become a second place a value is
declared, and the property being protected is that there is one.

## Two limits, both current

| limit | consequence |
|---|---|
| Paper has no theme modes yet. Dark mode is on their roadmap, not shipped | A Paper file holds one mode. Every token here is a `light-dark()` pair, so the file carries one half of each. Build the dark half, because it is the one the screenshots are taken in, and check light in the browser |
| Token types are colour, radius, spacing, container, breakpoint, font family, weight and size, line height, letter spacing | `--duration` and the three `--scope-*-edge` gradients are none of those, and Paper drops a `background-image` declaration outright. The edge textures are the load-bearing half of the provenance mark: draw them as inline SVG per artboard and accept that they do not tweak centrally. See **The first pass, as built** |

Tokens do not sync between Paper files. Keep everything in one file.

## Rules this project inherits

`~/dev/css-fun-experiments` is a sibling project whose design rules apply here. The ones that transfer:

| rule | here |
|---|---|
| generated loses to source | an artboard that disagrees with the running page is stale, and the page wins |
| a claim loses to a measurement | contrast is measured, not asserted. Every ink-on-ground pair gets a ratio in both schemes |
| the reference page proves it | the design surface is `tokens.css` alone. A look that needs a component change is a look that failed |
| two readers, one of them a machine | every page stays prerendered static HTML. No design change may move content behind script |

## Paper

The Paper desktop app serves an MCP server on `127.0.0.1:29979`, and only while a document is open in it.
Registered at user scope:

    claude mcp add paper --transport http http://127.0.0.1:29979/mcp --scope user

| step | |
|---|---|
| 1 | open a document in the Paper desktop app. The server starts with it |
| 2 | `claude mcp list` shows `paper ... ✔ Connected` |
| 3 | restart the Claude Code session. Servers are loaded at startup, so the tools appear on the next session, not this one |
| 4 | verify with "create a red rectangle in Paper" |

24 tools. The read half is `get_selection`, `get_jsx`, `get_screenshot`, `get_computed_styles`,
`get_tree_summary`, `export`. The write half is `create_artboard`, `write_html`, `set_text_content`,
`update_styles`, `move_nodes`, `duplicate_nodes`, `delete_nodes`. Paper exports real HTML and CSS, which
is why the read half is usable: a computed style read off a canvas is a value that can be typed into
`tokens.css` unchanged.

## The pass

| step | who | produces | status |
|---|---|---|---|
| 1 | design agent | `docs/design-theme.md`: a diagnosis from its own screenshots, and a complete proposed `tokens.css` | done |
| 2 | operator | accepts, or names what is wrong | done, serif rejected |
| 3 | agent | applies the accepted block to `tokens.css` | done, see **As applied** in the proposal |
| 4 | agent | rescreenshots every route, light and dark, at 1440px and 390px | partial, 1440px dark only |
| 5 | agent | mirrors the shipped tokens into Paper as artboards | done, 13 artboards |

Step 5 runs after step 3, never before. An artboard drawn from a proposal rather than from what shipped is
a claim, and the rule above says a claim loses to a measurement. The proposal is stale in two places for
exactly this reason; read **As applied** before drawing anything.

## Starting the Paper session

Paper's tools load when a session starts, so step 5 needs a fresh session in this repository, with a
document already open in the Paper desktop app. Paste this:

    Read docs/design-process.md, then the "As applied" section of docs/design-theme.md.
    site/src/lib/tokens.css is what shipped; the proposal above that section is not.

    Start the site:
        cd site && PUBLIC_OVERLAY_SOURCE=corpus.example npm run dev
    That flag is what makes the overlay marks and the reading level switch appear.

    Then, in one Paper file:
      1. Create Paper tokens from tokens.css, dark half of each light-dark() pair.
      2. Build every artboard under "What to build", reading those tokens.
         Read each page's real markup by fetching the prerendered HTML off the running
         site, do not invent layout. get_jsx reads Paper nodes, not a web page.
      3. Report which tokens had no Paper type and how you drew them instead.

    Do not edit tokens.css this session. The point is to be able to tweak in Paper first.

Read the tokens off the running page with `getComputedStyle`, not by parsing `tokens.css`. A token that
resolves through `light-dark()` has two values in the file and one on screen, and the artboard needs the
one on screen.

## What to build

Every route, rebuilt as an artboard reading the tokens, plus the token screens. The routes are the reason
the token screens are useful: a spacing step that looks fine in isolation is judged on `/filters`.

| artboard | is |
|---|---|
| `/` | hero, the traps table, the uses table, the three facts |
| `/filters` | the densest page. One family table and one value matrix is enough |
| `/field-types/<slug>` | an entry page: verdict rail, prose, inline literals, a wide table |
| `/findings` | a list: name, verdict, tags, one row per entry |
| `/findings/<slug>` | the other entry page. Same shell, different body: run-in labels, a payload slab, a bulleted list |
| `/how-it-works` | prose and tables at three heading levels |
| `/reference` | the shortest page, and the one most exposed by a spacing change |
| Type scale | seven steps at real size, both faces, each labelled with its token |
| Colour | every colour token, with the contrast ratio on each ink-on-ground pair |
| Density | one table at `--cell-y` / `--cell-x`, showing the 35px row |
| The mark | all three levels: word, edge texture, hue. Draw a greyscale copy beside it |

Build the routes at 1440px, then duplicate `/` and `/filters` at 390px. Read each page's real markup
with `get_jsx` off the running site rather than inventing layout, so an artboard is the page and not an
impression of it.

The mark artboard is the one to draw carefully. Colour is where the three levels look different;
greyscale is where the design still has to work, and the textures cannot be tokens, so nothing warns you
if one drifts.

## Keeping the two faithful

Faithful means one thing: an artboard and the live page render the same tokens. Checking it is a
comparison, not a promise.

| what | how |
|---|---|
| the values | `get_computed_styles` on an artboard against the running page. A difference means the artboard stopped reading a token and hardcoded a value |
| the screens | a Paper `get_screenshot` beside a Playwright screenshot of the same route at the same width |
| the marks | the API, Site and Project marks carry a word, an edge texture and a hue. An artboard that shows only the hue is not showing the mark |

Drift has one cause worth catching: an artboard that stopped reading a token and holds a literal instead.
That artboard stops responding to a theme change while still looking correct, which is the failure this
whole arrangement exists to avoid. Check it by changing one token and confirming every artboard moved.

## What a design change may not do

| never | why |
|---|---|
| rest meaning on hue alone | the provenance mark is three signals, and the texture is what survives greyscale and a reader who cannot separate the hues |
| add a theme toggle or a theme script | light and dark are one `light-dark()` declaration per colour, following `prefers-color-scheme` |
| declare a colour or a length outside `tokens.css` | the whole look changes from that file alone, and that is the property being protected |
| add a webfont without a licence | name an open face and its fallback stack, or stay on system faces |
| widen a page | wide content scrolls inside its own container. Every stacked grid declares `grid-template-columns: var(--col)` for this reason |

## Screens the pass covers

`/`, `/reference`, `/field-types`, `/field-types/[slug]`, `/entity-types`, `/entity-types/[slug]`,
`/filters`, `/recipes`, `/recipes/[slug]`, `/findings`, `/findings/[slug]`, `/how-it-works`.

`/filters` is the test. It is generated, it is the densest page on the site, and it holds one table per
data type. A theme that works there works everywhere.

Run the site with the example overlay to see the marks and the reading level switch, which a default local
build shows only if `corpus.local/` is populated:

    cd site && PUBLIC_OVERLAY_SOURCE=corpus.example npm run dev

## The first pass, as built

File: **sg-groundtruth — theme**, `https://app.paper.design/file/01M1J9NJKBVVMP1EH0DZCEAMSM`. Dark half,
one page, 55 tokens.

Thirteen artboards, laid out in one row at `top: -450px`, in reading order: the routes at 1440px, the two
phone widths, then the token screens.

| artboard | holds |
|---|---|
| `/` 1440 | the full page: header, hero, the setup prompt, the traps table, the uses table, the three facts, the four sections, footer |
| `/filters` 1440 | the header, the Numeric family table, the `color` value matrix, the jump nav |
| `/field-types/multi_entity` 1440 | the verdict rail, the run-in labels, a payload slab, the wide Write table |
| `/findings` 1440 | six rows: number, name, verdict, tags |
| `/findings/006_pagination` 1440 | the other entry page. Same shell as a field-type card, different body: the `Q` / `Endpoint` / `Docs claim` / `Actual` / `Teaches` run-in labels, a payload slab clipped at `--measure-wide`, and a bulleted list |
| `/how-it-works` 1440 | three heading levels, two tables, three slabs |
| `/reference` 1440 | the three group cards |
| `/` 390 | the header wrapped to three rows, the hero at its 42px clamp, the traps table clipped with a right-edge cue, the facts stacked |
| `/filters` 390 | the family table fitting with the operators wrapping, the value matrix scrolling inside its 36rem floor |
| The mark | three levels in colour and the same three in greyscale, side by side |
| Type scale | seven steps in both faces, plus the four leading tokens with a sample each |
| Colour | 17 swatches with both hexes, and 13 pairs with a measured ratio in each scheme |
| Density and space | the 35px row taken apart, and the eight space steps as bars |

The two 390px artboards are built, not duplicated. A duplicate of the 1440px page would carry its fixed
lane widths into a 390px frame, and an artboard that disagrees with the running page is stale. They are
drawn at the values the clamps resolve to at 390px: `--gutter` 16px, `--text-xl` 28px, `--text-display`
42px.

### Tokens with no Paper type

| token | drawn instead as |
|---|---|
| `--scope-api-edge`, `--scope-site-edge`, `--scope-project-edge` | an inline `<svg>` of `<rect>` stacks, one rect per dash, `fill` reading the level's colour token. Solid is one rect; site is 7px on, 5px off; project is 2px on, 4px off. The `viewBox` height is set to the node's real height so the pitch is 1:1 |
| `--measure`, and the `20ch` cap on the `/` h1 | a literal `ch` `max-width` on each node. `ch` resolves in Paper, so the wrap points match |
| `--col` | not needed. Artboards are flex, so no grid track has to be stated |
| `--duration` | not represented. Nothing on a canvas transitions |

### What Paper drops, silently

| what | evidence | consequence |
|---|---|---|
| `background-image` of any kind | `get_computed_styles` on a node written with `repeating-linear-gradient` returns the node's other properties and no `background-image` | the edge textures, the `.scroll-x` covers and cues, and the `--scroll-cue` gradient cannot be written as CSS. Use SVG |
| an SVG `<linearGradient>` | a `<rect fill="url(#id)">` renders as nothing | the scroll cue is drawn as six 4px `<rect>`s at stepped `fill-opacity` instead |
| `position: absolute` | an absolutely positioned edge strip inside a panel had no height | make the edge a flex sibling with `align-self: stretch`, not an overlay. The one place this costs something is the `.scroll-x` cue, which overlays on the live page and sits beside the table here |
| inline runs inside a paragraph | a `<p>` containing `<span style="color: var(--accent)">` renders as one Text node in the paragraph's own colour | an inline `<code>` or link inside a sentence cannot take the accent or the mono face, and the bold run-in labels (`**Read**`, `**Write**`) have to sit on their own line. Pages that are 40 to 60% literals lose that texture on the canvas. The `/field-types/multi_entity` artboard carries a grey bar at the top saying so: it is a canvas note, not page content, and it is the only thing on any artboard that is not on the live page |

### Two things to know before the round trip

| | |
|---|---|
| the four leading tokens come back as percentages | `1.12` is stored as `112.00000000000001%`. A Theme-tab copy pasted into `tokens.css` needs these four re-typed by hand |
| `--font-text` has no face on this machine | `system-ui`, `ui-sans-serif`, `ui-monospace` and `SF Mono` all report unavailable to `get_font_family_info`. Paper's own default, listed as `System Sans-Serif`, renders as the macOS system face the site actually uses, so text nodes are left on it. Mono is set to `Menlo`, which is in `--font-mono`'s own fallback stack |

### Tool notes

| | |
|---|---|
| `create_artboard` | ignores its own `x` and `y` and auto-places. Reposition with `update_styles` and **`left`/`top`**, `{"left": "1600px", "top": "-450px"}`. `x`/`y` there are accepted and silently do nothing |
| a Text node keeps the height it was first measured at | a heading that rewraps to a third line after the frame settles overlaps what follows. `height: fit-content` does not fix it; set the height in px, `lines x line-height` |
| `write_html` | `mode: "insert-children"` does not always append last. Check the order and fix it with `move_nodes`, `{"nodeId": ..., "after": ...}` |
| `move_nodes` | reparents and reorders only. It takes `before`, `after` or `parentId`, never coordinates |
| `x-paper-clone` | works, and deep-copies SVG children. The `/filters` header and footer are clones of the `/` ones, so a change to either has to be made twice |

### The dev server this was drawn from

`corpus.local/` is populated on this machine, so a default `npm run dev` renders real site names into the
overlay marks and the reading-level switch. The artboards were drawn from a second server started with
`PUBLIC_OVERLAY_SOURCE=corpus.example` on port 5174, so every name on the canvas is from the reviewed
copy: `Big Buck Bunny`, `corpus.example/site/`, `corpus.example/projects/p70/`.
