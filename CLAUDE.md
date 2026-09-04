# sg-groundtruth

A corpus that makes an LLM good at Flow Production Tracking, and a thin client that uses it.

## Clean room

Never read: `~/dev/fpt-ai`, `~/dev/fpt-api`, `~/dev/flow-data-api-docs`, `~/dev/flow-data-sdk-python`, `~/dev/tk-*`.
Derive only from public Flow PT REST docs and this repo's own probes.

`fpt-api` is excluded because it is AGPL-3.0 and this repo must stay permissively licensable.

## The corpus is the product

`corpus/findings/`: how the API behaves. Produced by probes.
`corpus/recipes/`: a verified call and its real response. Produced by probes.
`corpus/endpoints/`: one card per REST call. What it takes, every status code it answers with, a real
response, the edge cases that live on the call. Produced by probes.
`corpus/INDEX.md`: generated. Read this first, always. Open an entry only when its one-liner falls short.

**Four ways in, one per thing a caller already knows.** An agent about to make a call holds the call, the
entity type, the field's `data_type` and the task. Three of those had a door and the fourth did not:
findings were addressed by probe number, which is the order the probes ran in and nothing a caller knows.

| you know | key | lives in |
|---|---|---|
| the call | `endpoint:` on the card, `endpoints:` on every finding and recipe | `corpus/endpoints/<slug>.md` |
| the entity type | the file name | `findings/entity_types/<Type>.md` |
| the `data_type` | the file name | `findings/field_types/<type>.md` |
| the task | `intent:` | `corpus/recipes/` |

Findings also carry `phase:` (`auth`, `protocol`, `schema`, `read`, `filter`, `write`, `upload`,
`observe`, `render`), the part of a session the finding bites in. The index and the site group by it, so
the listing itself teaches the shape of a session. The number stays the probe that produced it.

An endpoint card holds what is true of the **call**: the request contract, the status codes, a recorded
response, and the edge cases that belong to the call rather than to a data type or an entity type. It
never restates a finding. The verdict of every entry naming that endpoint is joined onto the card by the
index and the site, so the quirks are on the page without being written twice.

`endpoint:` is the card's identity and the canonical spelling. `check_corpus.py` rejects an `endpoints:`
value no card is named by, so the two cannot drift, and a card is the unit a docs sweep adds: write the
card for a call the official documentation advertises and it lists with *no finding yet*, which is the
queue.

**Tags select or they are noise.** `trap` was on 61 of 81 entries once, and following it returned the
corpus. Two rules, both enforced: drop a tag every entry in the group already carries (`filter` on a
field-type card, which has a **Filter** section), and drop one that restates the entry's own name unless
another entry shares it (`percent` on `percent.md`, but `list-field` stays on `list.md`). An empty tag
list is a real answer on a matrix card. No subject tag may exceed 25 entries.

`silent`, `destructive` and `trap` are class tags: they name what kind of failure an entry is rather than
what it is about, so they are meant to span and the cap does not apply. `silent` is a 2xx that did not
carry out the request. `destructive` is a successful call that removes data the caller never named.

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

A `verdict:` states what was measured. It does not issue a rule the measurement does not carry.

The 200-character cap makes this easy to get wrong: a tally compresses into an imperative and the
qualifier is what gets dropped. Two entries did exactly this. `010_status_icons` ended on
"bg_color alone already draws a badge" while its body documented that the stock sprite is reachable
from the site's own stylesheet, so a reader following the index gave up one step early.
`018_project_listing` said to filter a project picker on `is_template`/`is_demo`/`archived` all
False, while its body only tallied the three as discriminators - and `is_demo` is True on exactly
one project, the demo show, which on this site is the richest one a picker would want.

Both read as complete, which is what made them expensive: the index exists so an agent can stop at
the one-liner, so a one-liner that reads finished while omitting the qualifier is worse than a
vague one. When the body describes and the verdict prescribes, the verdict is wrong.

An entry may also carry `coverage:`, one of `measured`, `partial` or `untested`. Absent means
`measured`. Anything else needs an `unmeasured:` line naming what was not reached, and the index and
the site put both on the row: an entry that reads like the rest while resting on a call nobody
completed is the one that costs a reader more than it gives. An endpoint card has to state it
outright, because a card is what a docs sweep adds before anything has been probed. `partial` is for
an entry whose calls were made but whose subject was not fully reached; `untested` is for a call
nobody has completed at all. Put the gap in the key, not only in a sentence in the body, and say
whether it is blocked on the work or on the site.

Every entry carries a `measured:` key as well, recipes included: one line saying where the evidence was
taken, a sample project, the sandbox project, or site-wide. `scope` says whether a claim transfers;
`measured` says what it rests on, and a `scope: api` claim can still rest on three rows the probe made in
the sandbox. Where the probe does not say, the key reads `unrecorded`. `_lib.emit` prints the line.

`corpus.local/` is the overlay, gitignored and generated: `site/` for what one site configures,
`projects/<id>/` for what one project does. The site reads all three and switches between them.

`corpus.example/` is a reviewed copy of one site's overlay, committed, so the public deploy has something
to show above the `api` level. `corpus.local/` is unchanged and still cannot reach a deployment; the copy
is separate so that stays true. Never copy into it without the review in `docs/example-overlay.md`, which
also carries why `build_overlay.py` leaving a stale project directory on disk is the leak that already
happened once.

Never code against `docs/quirks.md`. Those are unverified operator claims. A job that depends on one has a gap;
probe it.

## Probes

The REST docs are incomplete and sometimes wrong. Probe, record, then code against the finding.

- One question per probe: `probes/NNN_slug.py`
- Read-only by default. Writes require `--write`.
- **A probe leaves no trace.** Anything it creates, it deletes before it exits. Use `_lib.Created`, which
  deletes in reverse order on the way out. Rows that outlive a run become data the next probe measures.
  Schema fields are the exception: `DELETE` retires one and the name stays taken, so a probe cannot
  clean up after itself there. Test on a stock field the site already has. Where a probe must create
  one, name it `sg_zzprobe_<nnn>_*`: only emptying the Trash page in the web interface frees the name,
  and the prefix is what tells the operator doing that which fields are litter.
- **A probe prints; it never writes the corpus.** The agent running it judges what is identifying and
  writes the finding by hand. `_lib.scrub` handles only what a string replace can do safely: site URL,
  script name, key, home directory, emails, tokens, presigned URLs. Names are judgment; see
  `.claude/commands/probe.md` for the rules and the finding template.
- Never rewrite an API error, a MIME type, a field name or a file extension. Those are the teaching content.
- Every probe that produces a usable call also records a recipe
- `python probes/check_corpus.py` then `python probes/index.py` after any probe
- Tags drive retrieval, so the vocabulary must not drift. Reuse an existing tag from `corpus/INDEX.md` or add
  one deliberately. Singular, lowercase: `version`, not `versions` or `Version`. The two selection rules
  above are enforced, and so is the 25-entry cap.
- Every finding and recipe names its `endpoints:`. A call with no card in `corpus/endpoints/` is a card to
  write there first.
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

## The corpus over MCP

`python -m sg_groundtruth.mcp` serves the corpus to an agent: stdio, JSON-RPC, standard library only, no
dependency. Five tools, `scope: api` alone unless given `--overlay`. `corpus_endpoint` takes the call the
agent is about to make in any spelling, normalises `POST /entity/shots/_search` to
`POST /entity/<type>/_search`, and answers with the purpose, a sample and every entry behind it. `docs/mcp.md` carries registration,
the tool list and what has and has not been tested. It answers what the API does; a Flow PT MCP server
calls the API, and an agent holding both has to be told which is which.

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
