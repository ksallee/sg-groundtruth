# Plan

Covers both repos. `fpt-llm-api` is the corpus and client; `comfyui-fpt` is the node and first consumer.
Phases 0 and 1 happen entirely here. `comfyui-fpt` comes alive at Phase 2.

## State

Both repos scaffolded. Auth proved (probe 001). Nothing built yet.

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

Writes — sandbox only, and see the litter warning in `docs/quirks.md`:

- [ ] 011 custom field creation: allowed types, `sg_` prefix, display to programmatic name mapping
- [ ] 012 trashed field collision: revive, type mismatch, rename recovery
- [ ] 013 media upload: how media actually attaches to a Version, step by step
- [ ] 014 attachments: arbitrary file (workflow JSON) on a Version
- [ ] 015 create Version
- [ ] 016 dotted reads on multi-entity targets (needed before Phase 2)

011 and 012 decide where provenance lives: real typed custom fields, filterable in Flow PT's own UI, or a JSON
blob in an existing text field plus an attachment. Do not design provenance storage before they land.

**011 and 012 change site-wide schema, not project data.** A sandbox project does not contain them.

## Phase 1 — inspector

- `src/fpt_llm_api/schema.py`: fetch, cache, digest, query CLI
- `inspect.py` turns 005, 007, 008, 009 into `profile.local.json` for one project
- `/inspect-site` command: agent runs it, explains findings in plain language, operator edits and confirms

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

- Probe 010 left a gap: no status on this site has an icon, so the standard-vs-custom icon branches are
  unverified. Setting one custom icon by hand unblocks it.


- Does ComfyUI re-evaluate `INPUT_TYPES` on refresh, or does a profile change need a restart? Decides whether
  re-inspection is live or requires a bounce.
