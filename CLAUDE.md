# sg-groundtruth

A corpus that makes an LLM good at Flow Production Tracking, and a thin client that uses it.

## Clean room

Never read: `~/dev/fpt-ai`, `~/dev/fpt-api`, `~/dev/flow-data-api-docs`, `~/dev/flow-data-sdk-python`, `~/dev/tk-*`.
Derive only from public Flow PT REST docs and this repo's own probes.

`fpt-api` is excluded because it is AGPL-3.0 and this repo must stay permissively licensable.

## The corpus is the product

`corpus/findings/`: how the API behaves. Produced by probes.
`corpus/recipes/`: a verified call and its real response. Produced by probes.
`corpus/INDEX.md`: generated. Read this first, always. Open an entry only when its one-liner falls short.

Every finding carries a `scope`. There are three levels, and the probes are what proved they are distinct:

| scope | true of | examples |
|---|---|---|
| `api` | any Flow PT site | operator vocabularies, create contracts, `links.next` never absent |
| `site` | one site | custom entities and their slots, custom fields, `valid_values`, `/preferences` |
| `project` | one project inside it | `hidden_values`, page settings and visible columns, fill rates |

Probe 009 is why the last two are not one: `valid_values` is byte-identical at every scope and only
`hidden_values` varies by project. "Which statuses can I use" has no site-level answer.

Only `api` ships publicly. Inside an `api` finding, an individual site measurement is attributed inline,
beginning "On the probed site, ...". A `project` entry names its project in a `project:` key.

Every entry carries a `measured:` key as well, recipes included: one line saying where the evidence was
taken, a sample project, the sandbox project, or site-wide. `scope` says whether a claim transfers;
`measured` says what it rests on, and a `scope: api` claim can still rest on three rows the probe made in
the sandbox. Where the probe does not say, the key reads `unrecorded`. `_lib.emit` prints the line.

`corpus.local/` is the overlay, gitignored and generated: `site/` for what one site configures,
`projects/<id>/` for what one project does. The site reads all three and switches between them.

Never code against `docs/quirks.md`. Those are unverified operator claims. A job that depends on one has a gap;
probe it.

## Probes

The REST docs are incomplete and sometimes wrong. Probe, record, then code against the finding.

- One question per probe: `probes/NNN_slug.py`
- Read-only by default. Writes require `--write`.
- **A probe leaves no trace.** Anything it creates, it deletes before it exits. Use `_lib.Created`, which
  deletes in reverse order on the way out. Rows that outlive a run become data the next probe measures.
  Schema fields are the exception: a deleted field name is never freed (`docs/quirks.md`), so never create
  one to test with.
- **A probe prints; it never writes the corpus.** The agent running it judges what is identifying and
  writes the finding by hand. `_lib.scrub` handles only what a string replace can do safely: site URL,
  script name, key, home directory, emails, tokens, presigned URLs. Names are judgment; see
  `.claude/commands/probe.md` for the rules and the finding template.
- Never rewrite an API error, a MIME type, a field name or a file extension. Those are the teaching content.
- Every probe that produces a usable call also records a recipe
- `python probes/check_corpus.py` then `python probes/index.py` after any probe
- Tags drive retrieval, so the vocabulary must not drift. Reuse an existing tag from `corpus/INDEX.md` or add
  one deliberately. Singular, lowercase: `version`, not `versions` or `Version`.
- Code cites entries: `# probe 004`

Schema-writing probes use `sg_zzprobe_<nnn>_*`. See `docs/quirks.md`.

## Schema cache and inspector

Ask; never read the raw dump. `.schema-cache/<site>/<site|pNNN>/` holds the JSON, gitignored, refreshed
only with `--refresh`.

    PYTHONPATH=src python -m sg_groundtruth.schema entities --custom          enabled CustomEntityNN and their display names
    PYTHONPATH=src python -m sg_groundtruth.schema fields Version --editable  one type at a time; the expensive call (probe 002)
    PYTHONPATH=src python -m sg_groundtruth.schema --project N field Version sg_status_list
    PYTHONPATH=src python -m sg_groundtruth.schema --project N statuses Version

`inspect_site.py` measures one project and proposes a profile; `/inspect-site` is the operator-facing
version of the same run. It proposes with evidence and never decides. See PLAN Phase 1.

## The local overlay

`probes/build_overlay.py` writes `corpus.local/`, which the site reads as its `site` and `project`
reading levels. Read-only, re-runnable, and it replaces each tier wholesale.

    python probes/build_overlay.py                 site tier, then every FPT_PROBE_SAMPLE_PROJECTS project
    python probes/build_overlay.py --site          site tier only
    python probes/build_overlay.py --project 70    one project, plus the site tier
    python probes/build_overlay.py --refresh       re-fetch the schema cache instead of reading it

Its output is deliberately **not** scrubbed. `corpus.local/` is gitignored and never deployed, and real
slot numbers, display names and vocabularies are the entire point of it. `probes/check_corpus.py` lints
`corpus/` only. The file layout and frontmatter are the contract in `site/README.md`.

## Stack

Python 3.11, `requests`. A new dependency needs a line in DESIGN.md.

## Secrets

`.env.local`, gitignored, never printed. `FPT_API_SITE_URL`, `FPT_API_SCRIPT_NAME`, `FPT_API_API_KEY`.

Probe targets live there too, because a project id is site data exactly as a project name is:
`FPT_PROBE_SAMPLE_PROJECTS` (read-only targets, names or ids mixed, most interesting first),
`FPT_PROBE_SANDBOX_PROJECT` (the only project a probe may write into), `FPT_PROBE_FRAMES_DIR` (probe 022).
Never hardcode a project in a probe. `_lib.sample_projects` and `_lib.sandbox_id` resolve them.

## Style

Terse. Comments explain why, never what. Say a thing once, in one place.

**The corpus is public documentation.** It is read by people and models deciding how to call this API, and it
competes with the official docs. Write it to win that comparison.

- State the fact. No preamble, no restatement, no summary of what you just said.
- One explanation per fact, in one place. A second pass at the same idea means the first one failed. Fix it.
- No metaphors for data. A field **is returned under** `relationships`; it does not arrive, land, travel,
  carry, ride or live anywhere.
- No emphasis words: simply, essentially, basically, obviously, actually, really, just, of course.
  No `note that`, no `worth noting`, no `the whole point`.
- No ALL-CAPS for emphasis. Capitals are for API literals only: `NULL`, `PUT`, `CustomEntity19`.
- Bold only a term being defined or a genuine hazard. Not for volume.
- Give the number, the status code and the error string verbatim. They are the argument; adjectives are not.
- Say what a caller should do. "Subtract `hidden_values` yourself" beats "the API is permissive here".
- No rhetorical scaffolding. The evidence is on the page; do not announce it. Cut "that error is the proof",
  "which is why", "in other words", "the takeaway", "crucially". Show the error, state the rule, stop.
- **Attribute every site measurement inline.** `scope:` marks the file; a single sentence inside an `api`
  file can still be local. Counts, field censuses, fill rates and "there are N of these" all begin
  "On the probed site, ...". A reader forking this repo must be able to tell, sentence by sentence, what
  transfers to their site and what they have to measure again.
- Name the product **Flow Production Tracking** in full on first use, **Flow PT** after. Never `FPT`.
  `FPT_API_*`, `sg_groundtruth` and the `FPT` client class are identifiers and stay as they are.
- No em dashes. They join two thoughts that should be two sentences. Recast:
  a full stop when both halves stand alone, a colon when the second explains the first, commas or
  parentheses for an aside. If none of those fit, the sentence needs rewriting, not punctuating.

**Enumerations are tables, never sentences.** Whenever a section lists what happens for several inputs,
give one row per input. Prose that walks through cases in sequence is the single most common failure.

Wrong:

> **Clear** null clears. "" is also accepted, at 200, and stored as null — the empty string does not survive
> the round trip, so there is no "set but blank" state to read back. Omitting the key from a PUT leaves the
> field alone; it is not a clear.

Right:

> **Clear**
>
> | sent | result |
> |---|---|
> | `null` | cleared |
> | `""` | 200, stored as `null` |
> | key omitted from the PUT | unchanged |
>
> There is no "set but blank" state: `""` and `null` read back identically.

The table is the content. A sentence after it earns its place only by saying something no row can.

`probes/check_corpus.py` enforces the banned register mechanically.
