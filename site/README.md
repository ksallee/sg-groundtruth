# site

The public documentation site for the corpus. SvelteKit, prerendered to static HTML.

First draft. Layout and content are settled; the visual design is a placeholder meant to be replaced.

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

| source | committed | filter | renders as |
|---|---|---|---|
| `corpus/` | yes | `scope: api` only | the public site |
| `corpus.local/` | no, gitignored | `scope: site` only | labelled bands, plus `/site` |

`corpus/findings/` and `corpus/findings/field_types/` and `corpus/recipes/` each become a route. Frontmatter
supplies the one-line verdict and the tags; the body is rendered to HTML at build time.

Two shipped findings are `scope: site` (`005_link_usage`, `007_fill_rates`). They are measurements of one
Flow PT installation, so they are excluded from this site and never appear as a public fact. That exclusion
is the whole reason the `scope` field exists.

### The local overlay

Someone who clones this repo and points it at their own Flow PT site can build a version of these docs that
also covers that site: their custom entities, their status vocabularies, their fill rates, examples from
their own data. Drop markdown into `corpus.local/` at the repository root and rebuild. Nothing has to be
registered.

    corpus.local/findings/<nnn>_<slug>.md          a measurement of one site
    corpus.local/findings/field_types/<type>.md    keyed to a data_type name
    corpus.local/recipes/<nnn>_<slug>.md           a call made against one site

Required frontmatter, the same shape the shipped corpus uses:

    ---
    tags: [version, status]
    scope: site
    verdict: One line. What a reader of this site should do.
    ---

    # <heading>

How a file is picked up:

| file | renders |
|---|---|
| slug matches a shipped entry | on that entry's page, in a labelled band below the shipped card |
| slug matches nothing shipped | in full on `/site`, under an anchor |
| `scope` is not `site` | skipped, with a warning on the build log |
| directory absent or empty | nothing changes; the public build is this case |

An absent overlay is the normal case and is a first-class one: no dead links, no empty sections, and the
`This site` nav entry is not rendered at all. `/site` still exists in that state and explains the contract,
so someone who cloned the repo lands on instructions rather than a blank page.

`corpus.local/` is gitignored, so it is never committed and therefore can never reach a public deployment.
That is the whole enforcement mechanism; there is no runtime check.

The generator that populates the overlay lives in `probes/` and is deliberately not part of this site. The
site consumes the contract above and does not care what wrote the files.

## Which files are design surface

Touch these first.

| file | what it decides |
|---|---|
| `src/lib/tokens.css` | **every** colour, spacing step, font stack, radius, width and duration |
| `src/app.css` | base element styles, reads tokens and declares no values |
| `src/lib/components/*.svelte` | one concern each, styles scoped in the component |
| `src/routes/**/+page.svelte` | page composition and copy |

Every component reads tokens. Nothing hardcodes a colour or a length, so the whole look changes from
`tokens.css` alone. Light and dark come from one `light-dark()` declaration per colour and follow
`prefers-color-scheme`. There is no theme toggle and no theme script.

The components:

| component | does |
|---|---|
| `SiteHeader` / `SiteFooter` | the shell |
| `Section` | one band of a page: mono label, headline, lede, slot |
| `EntryList` | the corpus index as a list of name, verdict, tags |
| `EntryDetail` | one entry in full, plus its local overlay if there is one |
| `Prose` | rendered corpus markdown, and all the table and code-slab styling |
| `LocalBand` | wraps anything that came from the overlay, so it can never be read as an API fact |

## Which files are content plumbing

Leave these alone unless the pipeline itself is the problem.

| file | what it does |
|---|---|
| `src/lib/content/sources.js` | the seam: the two content roots and the scope rules |
| `src/lib/content/corpus.js` | reads, parses frontmatter, renders markdown, merges the overlay |
| `src/lib/site.js` | repo URL, and which field type is sampled on the landing page |
| `svelte.config.js`, `vite.config.js`, `vercel.json` | build and deploy |

## Routes

| route | on it |
|---|---|
| `/` | what it does, what it is for, how it works, enabling it for your site, cited examples, the field-type index, one card in full, findings, recipes |
| `/field-types` | every data type with verdicts and tags |
| `/field-types/[slug]` | one reference card in full |
| `/findings` | the numbered corpus, plus recipes |
| `/findings/[slug]` | one finding in full |
| `/recipes/[slug]` | one recipe in full |
| `/use` | pointing a model at it, running the probes, the scope field, the overlay contract |
| `/site` | local measurements, or the overlay contract when there is no overlay |

## Deployment

Public deploys go to Vercel from the `prod` branch only.

`vercel.json` enforces that in two ways: `git.deploymentEnabled` disables `main`, and `ignoreCommand`
exits non-zero (build) only when `VERCEL_GIT_COMMIT_REF` is `prod`, and exits zero (skip) for every other
branch. A push to any branch but `prod` produces no deployment.

Still to be set in the Vercel dashboard, because it cannot be expressed in the repository:

- **Root Directory** must be `site`. Without it Vercel builds the repository root and finds no app.
- **Production Branch** must be `prod`. Vercel treats the repository's default branch as production
  otherwise, and `ignoreCommand` would then skip every build with nothing ever promoted.
- Connect the Git repository, and leave preview deployments on. `ignoreCommand` is what suppresses them,
  which keeps one mechanism rather than two.

Verify after the first deploy that a push to a non-`prod` branch shows as skipped rather than built.

## Dependencies

Five build dependencies and one runtime one.

`marked` renders the corpus markdown. `mdsvex` is the conventional SvelteKit choice and was the obvious
first pick, but it compiles markdown as a Svelte component, which makes `{` and `}` in the source into
Svelte expressions. The corpus is full of them: `{type, id}` hashes, `{"multi_entity_update_mode": "add"}`,
JSON payloads in prose as well as in code spans. Seven corpus files already carry braces outside a code
fence. Under mdsvex any one of them breaks the build, and the corpus is edited by probes rather than by a
person watching the site. `marked` renders a string to a string and cannot be broken by content.

## Left undecided

- **No syntax highlighting.** Code blocks hold JSON, Python, HTTP and raw Ruby error strings, often in one
  block. Picking one language per block is a content decision, and a highlighter is a dependency and a
  colour system of its own. Slabs are monospace on a dark ground and nothing more.
- **The corpus marks its sections with bold, not headings.** `**Read**`, `**Write**`, `**Clear**`,
  `**Filter**`, `**Traps**` open a paragraph. They cannot be styled as real section heads without either
  editing the corpus to use `###` or pattern-matching bold-leading paragraphs. Left as plain bold. Noted in
  `Prose.svelte`.
- **The three counts in the hero.** Honest and they answer "how big is this", but a row of numbers is the
  most conventional gesture on the page. Cut them if they read as marketing.
- **No search and no tag index.** Tags render but do not link. At 39 entries browsing works; past a hundred
  it will not.
- **No `llms.txt` and no per-page raw markdown link.** Every page is prerendered static HTML and each entry
  links to its source markdown on GitHub, which covers the machine reader for now.
- **Typography is system faces.** `--font-text` and `--font-mono` are one line each in `tokens.css`.
- **`/site` is `noindex` but not otherwise protected.** It is harmless in a public build, where it holds
  only the contract.
