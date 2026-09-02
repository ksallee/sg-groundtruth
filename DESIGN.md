# Design

## Thesis

Three MIT-licensed Flow PT MCPs exist: `loonghao/shotgrid-mcp-server` (the incumbent, on PyPI),
`huikku/shotgrid-mcp` (a lean repackaging of it), and `rfletchr/ShotgunMcpGo`. Checked 2026-09-01.

The last already ships guidance — a hand-written `query_guide.md` plus an `sg_initialize` tool returning
"gotchas". So "MCPs give access without knowledge" is false, and this repo is not differentiated by having a
knowledge layer at all.

It is differentiated by what kind of knowledge, and how much:

- **Verified, not recalled.** Their guides are an author's recollection, undated, never checked against a live
  site — the same category this repo calls `docs/quirks.md` and refuses to code against. Every entry here comes
  from a probe that ran.
- **The wounds, not the basics.** They cover entity types, field discovery, filters, dot notation. Nothing
  covers trashed-field collision, the revive/type-mismatch state machine, `sg_` name mangling from display
  names, `CustomEntityNN` resolution, array-vs-hash negotiation, or per-project status opacity.
- **The write path.** They are read-focused with dry-run gates. The multi-step media upload and attachment flow
  is undocumented everywhere.
- **Recipes.** A verified call with its real response is a different artifact from a guide.

Re-check this section before making the claim publicly. It was wrong once.

## Two artifact types

**Findings** answer *how does the API behave* — one truth per entry, one actionable sentence as its verdict.
**Recipes** answer *how do I do X* — intent, the call, the real response, the gotchas.

Findings make a model reason correctly. Recipes make it act correctly. Both come out of probes; neither is
written by hand.

## Cheap index, expensive body

`corpus/INDEX.md` is generated and small enough to load whole. An agent reads it, then opens the two or three
entries it needs. An agent that must read the corpus to answer one question burns its context on the first call
and is useless for the rest of the session.

The same pattern governs the schema cache: raw JSON on disk, a compact digest over it, and a query CLI. The
agent asks; it does not read.

## Provenance mapping

Where a piece of provenance lands in Flow PT is the operator's decision, not this project's. One studio has
`sg_seed` and `sg_model` already; another wants a JSON blob in `description`; another only cares about the
workflow attachment.

So the node ships a set of **source keys** it can extract from ComfyUI — model, prompt, negative prompt, seed,
sampler, steps, cfg, workflow JSON, input Version ids, user, timestamp — and the profile carries a mapping from
each to a destination:

    "seed"     -> {"field": "sg_seed"}          a real field
    "prompt"   -> {"blob": "description"}       merged into a JSON blob in a text field
    "workflow" -> {"attachment": true}          uploaded as an Attachment (probe 014)
    "cfg"      -> {"drop": true}                not tracked here

The agent proposes a mapping by inspecting the site — which fields exist, which are filled (probe 007) — and
the operator edits and confirms it. If they ask for a destination field that does not exist, *that* is when
field creation runs. Probes 016 and 017 are on-demand setup machinery, not a phase.

### Data-driven, with an eject hatch

One shipped node reads the mapping at load time and builds its inputs from it. It is not a code generator:
generated forks cannot receive upstream fixes, and this repo's whole value is that improvements travel.

For anything the mapping cannot express, an agent command ejects a bespoke node the operator owns outright.
Rare by design.

## Schema cache

The schema is the only source of truth for what a site calls things — which `CustomEntityNN` are enabled and
their display names, which fields exist, their types, per-project status lists. It changes when anyone adds a
field, so it is cached, timestamped and explicitly refreshable.

Per site *and* per project: some field configuration and every status list is project-scoped.

## Stack

Python 3.11 and `requests` for the corpus and the client. The site in `site/` is SvelteKit prerendered to
static HTML: `@sveltejs/kit`, `@sveltejs/adapter-static`, `@sveltejs/vite-plugin-svelte`, `svelte` and `vite`
to build, and `marked` to render the corpus markdown (not `mdsvex`, which compiles markdown as a Svelte
component and so breaks on the `{type, id}` braces the corpus is full of).

## Licence

Permissive, when it goes public. The whole positioning against AGPL tooling in this industry depends on studio
legal being able to say yes without reading anything. Nothing AGPL enters this repo, at any depth.

## Horizon

Do not assume a fourth MCP is the answer. All three incumbents are MIT, the industry is small, and being the
knowledge layer they consume is worth more than owning a competitor nobody installs. The corpus is
format-independent; they already have the plumbing.

Decide that after the corpus is good. Not before.

## Consumers

`comfyui-fpt` is the first, and the discipline: this repo grows only to serve something that ships. A beautiful
client nobody uses is the failure mode.
