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

## Schema cache

The schema is the only source of truth for what a site calls things — which `CustomEntityNN` are enabled and
their display names, which fields exist, their types, per-project status lists. It changes when anyone adds a
field, so it is cached, timestamped and explicitly refreshable.

Per site *and* per project: some field configuration and every status list is project-scoped.

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
