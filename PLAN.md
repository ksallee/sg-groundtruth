# Plan

Covers both repos. `sg-groundtruth` is the corpus and client; `comfyui-fpt` is the node and first consumer.
Phases 0 and 1 happen entirely here. `comfyui-fpt` comes alive at Phase 2.

## State

Phase 0 read and write probes done. Phase 1 done: schema cache, CLI, inspector, `/inspect-site`.
`comfyui-fpt` has `FPT Publish Version` publishing end to end, so Phase 2 ran ahead of Phase 1.

**Big Buck Bunny (70) is the inference sample, and stays read-only.** Probes 004/005 measure which fields are
actually filled; writing test Versions into it would skew the statistics the inspector reads.

Writes go to our own project, created in Phase 3 and seeded with our own generated media — which also keeps the
public demo clear of anyone else's asset licensing.

## Phase 0 — prove the API  *(read half done)*

No product code. Read-only. Every finding cited later by the code that depends on it.

- [x] 001 auth, token lifetime
- [x] 002 schema: full site schema — size, shape, cost to fetch
- [x] 003 query shape: deep-linked and bubbled fields (`sg_task.Task.content`), filters, paging
- [x] 004 array vs hash: which header controls entity/multi-entity representation
- [x] 005 link usage: on BBB, what do Versions actually attach to, and at what rate
- [x] 006 pagination: does links.next terminate
- [x] 007 fill rates: which Version fields are populated on recent entries
- [x] 008 custom entities: which `CustomEntityNN` are enabled, and their display names
- [x] 009 status lists: per-project values, and what REST cannot see or set
- [x] 010 status icons and colours (Status entity)
- [ ] ~~009 old~~ per-project values, and what REST cannot see or set

Writes — sandbox project `comfyui-fpt sandbox` (id 1180), never BBB:

- [x] 011 create Project: only `name` is mandatory
- [x] 012 create Version: entity links are `{type, id}`
- [x] 013 media upload: three-step presigned flow, thumbnail vs media field
- [x] 014 attachments: arbitrary file as an Attachment entity
- [ ] 015 dotted reads on multi-entity targets (needed before the node reads parents)

On demand, not scheduled — both permanently burn field names site-wide, so they run only when an operator
maps provenance to a field that does not exist yet:

- [ ] 016 custom field creation: allowed types, `sg_` prefix, display to programmatic name mapping
- [ ] 017 trashed field collision: revive, type mismatch, rename recovery

Where provenance lands is the operator's mapping, not a project default. See DESIGN.md.

**The write path is proven end to end.** The node can be built.

Endpoint surface, recorded per call rather than per question:

- [x] 041 endpoint surface: every call's request contract, status codes and real response.
      Read-only by default; `--write` covers create, update, delete, batch and the three upload steps
      in the sandbox. The four schema-writing endpoints are deliberately absent, because a deleted
      field name is never freed, and their recorded output is in 019 and 040.

## Phase 1 — inspector  *(done)*

- [x] `src/sg_groundtruth/schema.py`: fetch, cache, digest, query CLI
- [x] `inspect_site.py` turns 005, 007, 008, 009, 018, 020 into `profile.local.json` for one project
- [x] `/inspect-site` command: agent runs it, explains findings in plain language, operator edits and confirms

Named `inspect_site.py`, not `inspect.py`: a top-level `inspect.py` shadows the stdlib module for
everything imported after it, and `requests` is in that blast radius.

Verified against Big Buck Bunny: the inspector independently reproduces probe 005 (`entity` 100%, Shot 99
Asset 1, `sg_task` 1%) without being told the answer.

**Two passes, for a measured reason (probe 020).** Fill rate alone is misleading: on BBB, 13 of the 18
fields at ~100% are system fields or checkboxes reading full because `False` is not null, while `image`
and `sg_uploaded_movie` — the fields the node actually writes — sit at 1%. So:

1. **Broad pass** — one paged fetch of recent Versions, count non-null per field. ~700ms for everything.
   Filter by schema first: `editable` drops computed fields, `data_type` excludes checkboxes from
   ranking, `mandatory` is a requirement rather than a heuristic.
2. **Shortlist pass** — `_summarize` with `grouping` per candidate, for cardinality. A field with one
   distinct value carries no information; one distinct value per row is an identifier. ~300ms each, so
   this runs over ~10 candidates, never all 61.

Ranking produces a shortlist with evidence. The operator confirms it; nothing here decides alone.

## Phase 2 — node (in `comfyui-fpt`)

- `provenance.py`: model, prompt, seed, sampler, graph, input Version ids, out of the ComfyUI prompt object
- `FPT Publish Version`, inputs built from the profile
- Install into ComfyUI, publish end to end from a real graph

## Phase 3 — own project, loop, showcase (in `comfyui-fpt`)

- Create our project; seed shots, tasks and media generated with nano banana 2 via the higgsfield MCP
- First write probes land here
- `FPT Fetch Media`, round trip
- Recorded demo; publish repo, `probes/findings/` becomes the public cookbook

## Open

- Probe 010 resolved all three icon cases, but the sprite behind `image_map_key` is still unlocated — not
  under `/images/*`. Standard statuses render from `bg_color` + name until it is found; check the web app's
  CSS for the sprite reference.


- Does ComfyUI re-evaluate `INPUT_TYPES` on refresh, or does a profile change need a restart? Decides whether
  re-inspection is live or requires a bounce.
