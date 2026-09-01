# Design

## Thesis

Existing Flow PT MCPs give a model *access* without *knowledge*. It still guesses field names, filter syntax and
return shapes, and gets them wrong — because nothing it was trained on is verified against a live site.

This repo is the knowledge. Verified calls, real responses, recorded gotchas, from probes run against an actual
site. A model reading it outperforms one reasoning from training data or poking a generic API proxy.

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

An MCP that serves the corpus, not just the API. Every Flow PT MCP so far is a thin proxy; one that answers
"how do I query X" with a verified example is a different category of thing. Not now — the corpus has to exist
and be good first.

## Consumers

`comfyui-fpt` is the first, and the discipline: this repo grows only to serve something that ships. A beautiful
client nobody uses is the failure mode.
