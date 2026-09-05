# site

The public documentation site for the corpus. SvelteKit, prerendered to static HTML.

Layout and content are settled. The visual design is on its second pass: one reading column, no
sidebars, three levels of ink. See "The look" below.

## Run it

    cd site
    npm install
    npm run dev        # http://localhost:5173, reads the corpus on every request
    npm run build      # static HTML into site/build/
    npm run preview    # serve the build

The build reads `../corpus/` off disk. It works from `site/` or from the repository root: the corpus is
found by walking up until a directory holds `corpus/INDEX.md`. If none is found the build fails loudly,
because an unfound corpus otherwise renders as a site that merely looks thin.

## Where the content comes from

Nothing on this site is written here. Every page is generated from markdown in `corpus/`.

The corpus has three levels of truth, and the probes are what proved they are distinct. Probe 009 is the
clearest case: `valid_values` is byte-identical at every scope and only `hidden_values` varies by project,
so "which statuses can I use" has no site-level answer.

| level | true of | source | committed | filter | renders as |
|---|---|---|---|---|---|
| `api` | any Flow PT site | `corpus/` | yes | `scope: api` | the public site |
| `site` | one Flow PT site | `corpus.local/site/` | no, gitignored | `scope: site` | marked rows and sections on the same pages |
| `project` | one project inside it | `corpus.local/projects/<id>/` | no, gitignored | `scope: project` with a `project:` key | marked rows and sections on the same pages |

Which directory the overlay is read from is `PUBLIC_OVERLAY_SOURCE`, defaulting to `corpus.local`. The
public deploy sets `corpus.example`, a committed copy reviewed by hand, so the deployed site has something
to show above the `api` level. `docs/example-overlay.md` carries the mechanism and the review it needs.

`/filters` is the one derived route with no directory behind it: it is built from the field-type cards and
throws at build time, naming the file, if a card records an operator its matrix never exercises.

`/endpoints` is a group like the others, reading `corpus/endpoints/`. Each card's page also renders the
verdict of every finding and recipe whose `endpoints:` names that call, joined by `measuredBy`. That join
is checked by `checkEndpoints`, which throws when an entry spells an endpoint no card is named by, so a
broken join fails the build rather than rendering a page that quietly lists less.

`/findings` groups by the `phase:` key rather than by number, in the order a client meets them. `PHASES` in
`src/lib/content/corpus.js` is that order, and `probes/index.py` holds the same list for `corpus/INDEX.md`.

`corpus/findings/`, `corpus/findings/field_types/`, `corpus/findings/entity_types/`, `corpus/recipes/`
and `corpus/endpoints/` each become a route. A `README.md` in one of those directories documents the
directory and is never read as an entry. Frontmatter supplies the one-line verdict and the tags; the body is rendered to HTML at
build time. A group is declared once, in `GROUPS` in `src/lib/content/sources.js`; adding one there gives the
overlay the matching directory for free.

Entity-type slugs are schema names, so they keep their capitalisation in the URL and in the heading:
`/entity-types/PublishedFile`, not a lowercased spelling of it. That is the string the API answers to.
Nothing in the site hardcodes how many entries a group has or which entries it holds; every count on a page
is read off the corpus at build time.

Two shipped findings are `scope: site` (`005_link_usage`, `007_fill_rates`). They are measurements of one
Flow PT installation, so they are excluded from this site and never appear as a public fact. That exclusion
is the whole reason the `scope` field exists.

### The local overlay

Someone who clones this repo and points it at their own Flow PT site can build a version of these docs that
also covers that site: their custom entities, their status vocabularies, their fill rates, examples from
their own data. Drop markdown into `corpus.local/` at the repository root and rebuild. Nothing has to be
registered.

    corpus.local/site/findings/<nnn>_<slug>.md                a measurement of one site
    corpus.local/site/findings/field_types/<type>.md          keyed to a data_type name
    corpus.local/site/findings/entity_types/<Type>.md         keyed to a schema name
    corpus.local/site/recipes/<nnn>_<slug>.md                 a call made against one site
    corpus.local/projects/<id>/findings/<nnn>_<slug>.md       a measurement of one project
    corpus.local/projects/<id>/findings/field_types/<type>.md
    corpus.local/projects/<id>/findings/entity_types/<Type>.md
    corpus.local/projects/<id>/recipes/<nnn>_<slug>.md

`<id>` is a directory name of your choosing and is what groups a project's files. The name shown to a reader
comes from the `project:` key the files carry, so a directory named `p101` can present itself as `Aurora`.

Required frontmatter, the same shape the shipped corpus uses. The scope has to match the directory.

    ---
    tags: [version, status]
    scope: site
    verdict: One line. What a reader of this site should do.
    ---

    # <heading>

An optional `title` names the thing the way a person does: `Lenses` for `CustomEntity19`, the schema name
for a standard type. It becomes the heading and the list label, and the slug stays beside it in both places,
because the slug is what a caller writes into a URL or a filter. The slug is also still the route, so
renaming a custom entity in the web interface moves no link. No shipped card carries the key, and without it
the slug is the label.

A project file carries one key more, naming which project it was measured on. `probes/check_corpus.py`
enforces it, and this site skips a file that omits it.

    ---
    tags: [version, status]
    scope: project
    project: <the project it was measured on>
    verdict: One line. What a reader of this site should do.
    ---

    # <heading>

How a file is picked up:

| file | renders |
|---|---|
| slug matches a shipped entry | in a marked section below the shipped card, and as a mark on that entry's row |
| slug matches nothing shipped | as a row of its own in the same list, and a page of its own, with no API section |
| `scope` does not match the directory | skipped, with a warning on the build log |
| `scope: project` with no `project:` key | skipped, with a warning on the build log |
| a project directory with no readable file | not offered as a reading level |
| directory absent or empty | nothing changes; the public build is this case |

An absent overlay is the normal case and is a first-class one: no dead links, no empty sections, no reading
level switch, and nothing marked, because at one level there is nothing to distinguish. The overlay contract
is on `/how-it-works#overlay` in every build, so someone who cloned the repo finds the instructions there.

`corpus.local/` is gitignored, so it is never committed and therefore can never reach a public deployment.
That is the whole enforcement mechanism; there is no runtime check. A public build shows an overlay only
by reading `corpus.example/`, a different directory that somebody reviewed and committed on purpose.

The generator that populates the overlay lives in `probes/` and is deliberately not part of this site. The
site consumes the contract above and does not care what wrote the files.

    python probes/build_overlay.py                 the site tier, then every FPT_PROBE_SAMPLE_PROJECTS project
    python probes/build_overlay.py --site          the site tier only
    python probes/build_overlay.py --project 70    one project, plus the site tier
    python probes/build_overlay.py --refresh       re-fetch the schema cache instead of reading it

It is read-only, re-runnable and replaces each tier wholesale, so a run that fails partway leaves the
previous overlay intact. A full run over two projects takes about a minute cold and half that once the
schema cache is warm. What it writes:

| file | scope | holds |
|---|---|---|
| `site/findings/008_custom_entities.md` | site | the enabled `CustomEntityNN` slots, their display names, their REST paths and their row counts |
| `site/findings/009_status_lists.md` | site | `valid_values` for every list, status and entity-type field, which is site-wide |
| `site/findings/019_create_fields.md` | site | every `sg_` field per entity type, with its data type |
| `site/findings/021_media_resolution.md` | site | the LocalStorage roots, and which `local_path_*` therefore resolve |
| `site/findings/101_preferences.md` | site | the `GET /preferences` keys, `hours_per_day` and `duration_units` first |
| `projects/<id>/findings/005_link_usage.md` | project | which link fields are set, and what they point at |
| `projects/<id>/findings/007_fill_rates.md` | project | fill rate per field per entity type |
| `projects/<id>/findings/009_status_lists.md` | project | `valid_values` minus `hidden_values`, per entity type |
| `projects/<id>/findings/023_pages.md` | project | each Page and its columns, ready to hand to `?fields` |

A slug that matches a shipped entry renders beside that entry's card; `101_preferences` matches nothing
shipped, so it is a findings row of its own; so are `005_link_usage` and `007_fill_rates`, whose shipped
counterparts are `scope: site` and never published. A `CustomEntityNN` card is a row in the entity types
list. Nothing local gets a page outside the list it is about.

The output is **not scrubbed**, unlike everything a probe prints. Its whole value is the real slot
numbers, the real display names and the real vocabularies, and `corpus.local/` is gitignored.

### The reading level

There is nothing to choose. A page shows every level the build holds, the API first, then the site, then
each project, each as a section under its badge. A public build has no overlay and shows the API alone.
Every count on the site answers at the deepest level the build holds.

### The badge

A section or a list row that is not the API alone carries a badge: the level's word on the level's colour.
Blue is the API, orange is one site, green is one project, and these three are the only hues on the site.
The sidebar carries the same colours as a dot beside every entry and as a key at its foot. A page with more
than one section has a list at the far right of the page, one row per section with its dot, that scrolls to
a section and follows the scroll. Each section's badge pins to the top of the viewport while its content
scrolls under it, over a fade `--pin-fade` tall, and hands over to the next section's badge.

Everything is declared in `tokens.css` under `--scope-*`, resolved by one `[data-scope]` rule in `app.css`,
and drawn by `ScopeMark` and `ScopeSection`.

## Which files are design surface

Touch these first.

Start with `src/lib/tokens.css`: every colour, length and face on the site is one line in it, so the whole
look changes from that file alone. Then the two pages that carry the most structure and the least prose,
`src/routes/+page.svelte` (the landing page, now a short stack of `Section` bands) and
`src/routes/filters/+page.svelte` (a generated table, the densest page on the site). `Prose.svelte` is third:
it styles every rendered corpus body, so a change there lands on every entry page at once.

| file | what it decides |
|---|---|
| `src/lib/tokens.css` | **every** colour, spacing step, font stack, radius, width and duration |
| `src/app.css` | base element styles, reads tokens and declares no values |
| `src/lib/components/*.svelte` | one concern each, styles scoped in the component |
| `src/routes/**/+page.svelte` | page composition and copy |
| `static/favicon.svg` | the mark, and the one place a colour is written outside `tokens.css` |

Every component reads tokens. Nothing hardcodes a colour or a length, so the whole look changes from
`tokens.css` alone. `static/favicon.svg` is the exception, and has to be: a favicon is fetched as its
own document, with no stylesheet and no custom properties, so the three accents are written into it. It
is the sidebar's dot row, one dot per reading level in `api`, `site`, `project` order, at the same 6px:4px
dot-to-gap ratio `Sidebar.svelte` draws, and it changes when those three accents do.

`static/apple-touch-icon.png` is that file at 180px, flattened, for the one place an SVG is not accepted.
It is a committed binary rather than a build step because the site has no rasteriser and adding one for a
1 KB file is not worth a dependency. Regenerate it by rendering `favicon.svg` at 180 by 180. The site is dark only: `color-scheme` is pinned to `dark` on the root, so every
`light-dark()` resolves to its second value. The light values stay in the tokens for the day that changes.

The components:

| component | does |
|---|---|
| `Sidebar` | the navigation: home, two pages, five groups that open, and the project the overlay was read from; a tooltip on an entry's dots names their levels |
| `SiteHeader` / `SiteFooter` | the phone's top bar with the menu button, and the footer |
| `Breadcrumb` | home, the section, the page: on every page but the intro |
| `CopyButton` | copies its text; the SDS copy stroke, a tooltip, and a ticked circle once copied |
| `Section` | one band of a page: mono label, headline, lede, slot |
| `EntryList` | the corpus index as a list of name, verdict, tags, each row marked with what it holds |
| `EntryDetail` | one subject in full: the API card, then what the overlay measured about the same subject |
| `Prose` | rendered corpus markdown, and all the table and code-slab styling |
| `ScopeMark` | the badge: the level's word on the level's colour |
| `ScopeSection` | one section of an entry page, under its badge |

Three accents, one per level: `--accent` for a shipped fact or a link, `--accent-local` for one site,
`--accent-project` for one project. Nothing rests on the hue alone: see **The mark** above.

## Which files are content plumbing

Leave these alone unless the pipeline itself is the problem.

| file | what it does |
|---|---|
| `src/lib/content/sources.js` | the seam: the three content roots and the scope rules |
| `src/lib/content/corpus.js` | reads, parses frontmatter, renders markdown, merges the overlay |
| `src/lib/reading.svelte.js` | the reading level: the deepest the build holds, and what that shows |
| `src/lib/site.js` | repo URL, the overlay directory a reader is told to create, and the one this build read |
| `src/lib/content/filters.js` | the operator vocabulary read out of each field-type card, and the families it groups them into |
| `src/lib/content/markdown.js` | the shipped file behind an entry, verbatim, and the `.md` URL it is served at |
| `src/lib/content/agents.js` | `llms.txt`, the section twins, the sitemap and robots |
| `src/lib/components/ReportStatus.svelte` | the five keys a report carries that no other group does |
| `svelte.config.js`, `vite.config.js`, `vercel.json` | build and deploy |

## Routes

The navigation is a sidebar on the left. Two entries are pages, Intro and How it works. Five open to
list what they hold: field types, entity types, filters, recipes, findings. The name at the top is home.

| section | route | is |
|---|---|---|
| Recipes | `/recipes` | a task and the calls that perform it, which is a different kind of thing from a reference card |
| Findings | `/findings` | what was learned, question by question, chronological, later entries correcting earlier ones |
| How it works | `/how-it-works` | the probes, the scope field, the overlay contract, the reading level |

| route | on it |
|---|---|
| `/` | the hero, the setup prompt, why it exists, what it does, three facts, and links to every section |
| `/field-types` | every data type with verdicts and tags |
| `/field-types/[slug]` | one reference card in full |
| `/entity-types` | every entity type with verdicts and tags |
| `/entity-types/[slug]` | one entity-type card in full |
| `/filters` | every filter operator the API accepts per data type, and the value each one takes, generated from the field-type cards |
| `/recipes` | every recipe |
| `/recipes/[slug]` | one recipe in full |
| `/findings` | the numbered corpus, then the cited examples |
| `/findings/[slug]` | one finding in full |
| `/reports` | every report as a table: kind, status and the date each was last confirmed |
| `/reports/[slug]` | one report in full, under a block naming its evidence |
| every list and `[slug]` above | grows with the reading level; a local-only entry is a row in the list it belongs to and a page under it |
| `/how-it-works` | pointing a model at the index, running the probes, the scope field, enabling it for your site, the reading level, using it alongside an MCP server |

The overlay has no route of its own and adds no nav entry. Only the reading level switch appears when the
build read one.

### Reports

`/reports` is the one list page that is not an `EntryList`. What a reader wants there is which of them
are filed and when each was last seen, and that is one row per report with a column each.

A report is joined to its evidence rather than restating it. `evidence:` in the frontmatter is the real
path under `corpus/`, which is what `probes/check_corpus.py` checks against the filesystem, and
`corpus.js` resolves it back to a page through `GROUPS`, longest directory first: `findings/field_types/
percent` starts with `findings/` as well. A report citing an entry this build excludes throws at build
time rather than rendering a dead link, the same rule `linksFor` applies to an endpoint card.

`EntryDetail` takes a `children` snippet, rendered under the header. `ReportStatus` is the only thing
passed to it today, and the component stays unaware of what it is.

### The machine door

A client that fetches rather than reads gets markdown. The rendered page is eleven bytes of markup per
byte of finding, and the only markdown link used to be a GitHub blob URL, which is another HTML page a
client has to know how to rewrite.

| route | is |
|---|---|
| `/llms.txt` | every published entry, one line each: name, the URL of its markdown, its verdict, and its coverage where it is not `measured`. The four doors and what each frontmatter key selects are above the list |
| `/[section].md` | one section's rows, under the grouping its page draws: findings by phase, endpoints by family |
| `/<section>/[slug].md` | `corpus/<dir>/<slug>.md` byte for byte, frontmatter included |
| `/sitemap.xml` | every rendered page, and no twin |
| `/robots.txt` | allow everything, and where the sitemap is |

Every one of them is prerendered, so a twin is a file in `build/` and no server runs to answer for it.

The frontmatter stays on a twin because it is the retrieval key: `scope`, `phase`, `endpoints`, `tags`
and `coverage` are what a client selects on, and a body without them is less than the repository holds.

`src/lib/content/markdown.js` reads the files and owns the `.md` URL of an entry. `agents.js` builds the
four generated routes on top of it and `corpus.js`. The group directory is written down once, in
`GROUPS` in `sources.js`: a second copy beside the markup is what put a dead
`corpus/findings/get_root.md` behind every endpoint card's source link.

One route file per group, three lines each, rather than a root `[section]/[slug].md`. A static
`findings/[slug]` outranks a dynamic `[section]`, so the shared route would hand `/findings/x.md` to the
HTML page as a slug ending in `.md`.

An entity-type card sets its own sections (`**Type**`, `**Identity**`, `**Create**`, `**Links**`,
`**Status**`, `**Traps**`) and they are not the field-type ones. `EntryDetail` renders whatever the markdown
holds and assumes no section, which is why the two groups share it.

### Where the Filters page comes from

`/filters` is generated at build time from the field-type cards, so it cannot drift from them.
`src/lib/content/filters.js` reads each card's markdown twice, and the corpus is never edited to make that
easier; other agents own those files.

The page answers two questions and separates them, because they read in different directions.

| part | question | shape | read out of |
|---|---|---|---|
| Operators, by family | which relations does a type accept | one table per family, all 24 types compared | the `Valid relations` list |
| Values, by data type | what do I send to this operator | one table per type | the `**Filter**` matrix |

A comparison is read across the types and a lookup is read down one type, so the second part is a section
per data type rather than a control to open: every type has a stable anchor, and nothing on the page is
hidden from a find-in-page. A type name in the comparison links to its section; the section heading links
to the card.

#### The operator vocabulary

A card states its vocabulary in one of three shapes, because it quotes the API's own 400 in whichever form
the probe printed it:

| in the card | example | types today |
|---|---|---|
| the pretty-printed error | `Valid relations: ["is", "is_not"]` | most of them |
| the raw JSON body, quotes still escaped | `Valid relations: [\"is\", \"is_not\"]` | `date_time`, `jsonb`, `uuid` |
| no list, and a 400 that reads `... data type cannot be used in a filter` | | `calculated`, `password`, `serializable`, `summary`, `url` |

A list may also wrap across lines inside a fence, so the match runs over the whole file rather than line by
line. Both quote forms are read by one token pattern, so the second shape needs no special case beyond
allowing the backslash.

A card that matches none of the three throws, and the build stops with the file named. The same happens when
a card quotes two `Valid relations` lists that disagree. An unparseable card must never become a blank row:
a reader cannot tell an empty cell from "this type accepts no operator", and the second is a real answer the
page publishes for five types.

Rows are grouped into families by the vocabulary itself rather than by a list of type names, so a data type
added to the corpus lands in the right family with no edit. A family whose members all return the identical
list says so, with the count read off the data.

#### The value matrix

Every filterable card holds a `**Filter**` matrix whose first three columns are
`| operator | value | matches |`. That shape is a contract rather than a habit: `probes/check_corpus.py`
enforces it, and this site is what it is enforced for. `value` is a literal a caller can paste, which is the
half the operator list cannot give: `in_last` takes `[7, "DAY"]` and not `7`.

The matrix holds more rows than the vocabulary holds operators, and both kinds are rendered. One operator
gets a row per value shape it accepts, and a card also records the operators the API refuses, whose
`matches` is the 400.

Three ways the page refuses to publish less than the corpus knows:

| in the card | on the page |
|---|---|
| a `Valid relations` list and no readable matrix | the build stops, with the file named |
| an operator in the list that no matrix row exercises | the build stops, naming the missing operators |
| a row reading `not measured` in `value` and `matches` | rendered as a marked gap, never blank and never dropped |

`not measured` is deliberate in the corpus: the operator is in the API's own list and the card never sent it.
One row reads that today, on `multi_entity.name_not_contains`.

Extra columns exist on some cards and are dropped here. `date` adds `measured`, `image` adds `code`, `uuid`
adds two row counts, and `multi_entity` records which of its four built rows matched. Each means something
different, so rendering them side by side under one heading would put four kinds of number in one column.
Each section names the columns its card adds and links to the card.

The five types the API refuses to filter enumerate no operators and so have no matrix. They render as "No
relation is accepted." in both parts.

## Deployment

Public deploys go to Vercel from `main` only. Work branches off `dev`, merges into `dev`, and reaches
`main` when it is agreed: see **Branches** in the repository README.

`vercel.json` enforces that with `ignoreCommand`, which exits non-zero (build) only when
`VERCEL_GIT_COMMIT_REF` is `main` and exits zero (skip) for every other branch. `git.deploymentEnabled`
lists `main` alone for the same reason, so a push to `dev` produces no deployment and `dev` is QA'd
locally with `npm run build && npm run preview`.

Still to be set in the Vercel dashboard, because it cannot be expressed in the repository:

- **Root Directory** must be `site`. Without it Vercel builds the repository root and finds no app.
- **Production Branch** must be `main`.
- Connect the Git repository, and leave preview deployments on. `ignoreCommand` is what suppresses them,
  which keeps one mechanism rather than two.

Verify after a deploy that a push to a non-`main` branch shows as skipped rather than built.

## Dependencies

Five build dependencies and one runtime one, plus one that exists for the dev server alone.

`agent-ui-annotation` draws a feedback toolbar on the dev server: click an element, write a note, copy every
note as one prompt for an agent. It is a custom element with `lit` as its only dependency, so the earlier
React toolbar's `react` and `react-dom` are gone. It is mounted from `src/lib/dev/annotation.js` behind
`import.meta.env.DEV`, so no build carries it.

`marked` renders the corpus markdown. `mdsvex` is the conventional SvelteKit choice and was the obvious
first pick, but it compiles markdown as a Svelte component, which makes `{` and `}` in the source into
Svelte expressions. The corpus is full of them: `{type, id}` hashes, `{"multi_entity_update_mode": "add"}`,
JSON payloads in prose as well as in code spans. Seven corpus files already carry braces outside a code
fence. Under mdsvex any one of them breaks the build, and the corpus is edited by probes rather than by a
person watching the site. `marked` renders a string to a string and cannot be broken by content.

## The look

One column, `--column` wide (700px), and nothing on any page is wider than it: header, content and footer
all sit in it, and a table or a slab that needs more room scrolls inside itself. There is no sidebar and no
table of contents. A page is read top to bottom. The sidebar is the one fixed element.

| decision | where |
|---|---|
| body text is 17px on a 1.6 line, tracked -1% | `--text-body`, `--leading-body`, `--tracking-body` |
| three inks: headings, emphasis and links in `--ink`; paragraphs in `--ink-body`; metadata in `--ink-muted` | `tokens.css` |
| warm graphite neutrals, dark only, with light values kept in the tokens | `tokens.css` |
| links underline in `--underline`, a lighter ink, and darken on hover | `app.css` |
| code boxes sit one step above the page inside a hairline of white at 8%, 12px radius, 14px mono at 1.6 | `--slab`, `--slab-rule`, `--slab-divider` |
| tables wrap their cells instead of scrolling, so a 300-character error string gets a taller row | `app.css` |
| the API mark takes the page's ink; only the two local levels carry a hue, amber and green | `--scope-*` |
| the system UI face and the system mono face, no webfont | `--font-text`, `--font-mono` |

**The corpus marks its sections with bold, not headings.** `**Read**`, `**Write**`, `**Clear**`,
`**Filter**`, `**Traps**` open a paragraph on a field-type card; `**Type**`, `**Identity**`, `**Create**`,
`**Links**`, `**Status**` on an entity type; `**Q**`, `**Endpoint**`, `**Actual**`, `**Teaches**` on a
finding. `Prose.svelte` sets `p > strong:first-child` on its own line with a section's worth of air above
it, so they read as heads. The markdown is untouched.

## Left undecided

- **No syntax highlighting.** Code blocks hold JSON, Python, HTTP and raw Ruby error strings, often in one
  block. Picking one language per block is a content decision, and a highlighter is a dependency and a
  colour system of its own. Slabs are monospace on a dark ground and nothing more.
- **The cited examples sit at the foot of `/findings`.** They are evidence for a reader who has already
  decided, and they belong beside the entries that recorded them rather than on the landing page. The MCP
  integrations sit on `/how-it-works`, under `#mcp`: they answer a question a reader already has rather than
  one they arrive with. `integrations` in `src/routes/how-it-works/+page.svelte` is still structure only, and
  the section renders nothing when the array is empty.
- **The five facts sit under "What it is", on the landing page.** Four of the five state what the thing does,
  and the privacy fact leads because it is stated nowhere else. How the thing was built is a page of its own.
- **`PERMISSIONS_CAVEAT` in `src/routes/+page.svelte` is one line, written from finding 027.** It renders
  under the five facts. It is a constant rather than prose because it is conditional: an empty string renders
  nothing.
- **`/filters` is flat, not `/reference/filters`.** `/reference` is an index over routes it does not own, so
  every reference route stays one segment and no link had to move when the index was added.
- **The landing page renders no overlay content, only counts.** A local build sees its overlay in the lists
  and on the entry pages. The front page states how many entries each section holds at the level in force,
  which is the whole of what it says about the overlay.
- **Family notes on `/filters` are written here, not read from the corpus.** The rows, the operators, the
  values, the counts and the grouping are all derived; the one-line note under each family heading is site
  copy, and it is the only prose on the page that a card does not supply.
- **No search and no tag index.** Tags render but do not link. At the corpus's current size browsing works;
  past a hundred entries it will not.
- **A twin is the shipped file, not the rendered page.** `/findings/026_result_order.md` is
  `corpus/findings/026_result_order.md` byte for byte, so an overlay a build merges into the HTML is
  absent from the markdown. One name, one set of bytes, wherever it is read from. A twin exists only
  where a shipped file does: a local-only subject has a page and no `.md`.
- **`/llms.txt` is the whole index, not a table of contents.** 44 KB, one line per entry with its
  verdict and the URL of its markdown, which is one fetch rather than a crawl. The section twins carry
  the same rows under the grouping their pages draw, for a client that already knows which section it
  wants.
- **The sitemap lists the rendered pages and never the twins.** A sitemap addresses a reader and
  `llms.txt` addresses a client; listing both spellings of one page asks a crawler to fetch it twice.
- **Typography is system faces.** `--font-text` and `--font-mono` are one line each in `tokens.css`.
- **Every stacked grid declares `grid-template-columns: var(--col)`.** A grid's default `auto` track is
  sized by its widest child's max-content, so one long table cell widened the whole page instead of
  scrolling inside its own container, and the percentages in `--measure` had nothing to resolve against.
- **There is no page that inventories the overlay.** The level is depth on the pages a reader is already on,
  so a local measurement is found where its subject is documented and nowhere else. Local-only entry pages
  exist in a local build alone and are never prerendered by a public one.
- **The level switch is not in the URL.** A link to a page carries no level with it, so a reader following
  one sees whatever they last chose. A query parameter would make a level shareable and would also make a
  local measurement linkable, which is the opposite of what the overlay is for.
