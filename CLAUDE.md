# fpt-llm-api

A corpus that makes an LLM good at Flow Production Tracking, and a thin client that uses it.

## Clean room

Never read: `~/dev/fpt-ai`, `~/dev/fpt-api`, `~/dev/flow-data-api-docs`, `~/dev/flow-data-sdk-python`, `~/dev/tk-*`.
Derive only from public Flow PT REST docs and this repo's own probes.

`fpt-api` is excluded because it is AGPL-3.0 and this repo must stay permissively licensable.

## The corpus is the product

`corpus/findings/` — how the API behaves. Produced by probes.
`corpus/recipes/` — a verified call and its real response. Produced by probes.
`corpus/INDEX.md` — generated. Read this first, always. Open an entry only when its one-liner falls short.

Never code against `docs/quirks.md`. Those are unverified operator claims. A job that depends on one has a gap;
probe it.

## Probes

The REST docs are incomplete and sometimes wrong. Probe, record, then code against the finding.

- One question per probe: `probes/NNN_slug.py`
- Read-only by default. Writes require `--write`.
- Sanitize before commit: no tokens, no site URL, no project or entity names
- Every probe that produces a usable call also records a recipe
- `python probes/index.py` after any probe
- Code cites entries: `# probe 004`

Schema-writing probes use `sg_zzprobe_<nnn>_*`. See `docs/quirks.md`.

## Stack

Python 3.11, `requests`. A new dependency needs a line in DESIGN.md.

## Secrets

`.env.local`, gitignored, never printed. `FPT_API_SITE_URL`, `FPT_API_SCRIPT_NAME`, `FPT_API_API_KEY`.

## Style

Terse. Comments explain why, never what. Say a thing once, in one place.
