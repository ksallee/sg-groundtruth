# Known quirks

Operator knowledge, recorded before probing. **These are claims, not findings.** Nothing here may be coded
against until a probe in `probes/findings/` confirms it. Each entry names the probe that will.

## Custom fields

| Claim | Probe |
|---|---|
| Custom fields can be created over REST | 009 |
| Not every type can — calculated and query fields are limited or impossible | 009 |
| All custom names are forced to an `sg_` prefix | 009 |
| Display name maps to a computed programmatic name; `Foo (Bar)` becomes something like `sg_foo__bar_` | 009 |
| Trashed fields cannot be listed | 010 |
| Creating a field can collide with a trashed field you cannot see | 010 |
| A trashed field can be revived | 010 |
| Reviving fails if the trashed field's type differs from the type you want | 010 |
| Recovery is: trash again, pick another programmatic name | 010 |

Consequence: field creation is a state machine, not a call — create, detect collision, attempt revive, check
type, on mismatch re-trash and rename. Encode it once, in one place, cited to 009 and 010.

**Probe fields are permanent litter.** Trashed names still collide and cannot be enumerated, so every schema
probe burns a name on the site forever. All probe fields use `sg_zzprobe_<nnn>_*` so they can never collide
with a name anyone would choose deliberately.

## Custom entities

| Claim | Probe |
|---|---|
| Custom entities cannot be enabled over REST | 007 |
| They are addressed by programmatic name, `CustomEntity07` and so on | 007 |
| Each site assigns those numbers differently — the number means nothing across sites | 007 |
| The real display name is in the schema | 007 |

Consequence: never hardcode a `CustomEntityNN`. Resolve display name to programmatic name through the schema
cache, per site.

## Statuses

| Claim | Probe |
|---|---|
| Status lists cannot be mirrored project to project over REST | 008 |
| The schema carries hidden values REST cannot control | 008 |

## Requests

| Claim | Probe | Outcome |
|---|---|---|
| Entity and multi-entity fields return array or hash form depending on request headers | 004 | **False for REST** |

Probes 004 and 014: **true, but it is a request `Content-Type` on `POST _search`, not an `Accept` header on
`GET`.** Those vendor types sent as `Accept` on a GET return 406; `POST /entity/<type>/_search` rejects
`application/json` with 415 and requires `application/vnd+shotgun.api3_array+json` or `...api3_hash+json`.
Responses are unaffected — entity fields always arrive under `relationships`.

## Projects

| Claim | Probe | Outcome |
|---|---|---|
| A project picker filters on `[["sg_status", "is", "Active"]]` | 018 | **false** — null on 15 of 22 projects here, including newly created ones |
| `is_template` / `is_demo` / `archived` identify projects a human would not publish into | 018 | **confirmed** |

`sg_status` has no `display_values` and is never set automatically. Filter the checkboxes; leave status alone.

## Summaries

| Claim | Probe | Outcome |
|---|---|---|
| Summarize calls are cheap and describe a field's values | 020 | **half true** — one call gives cardinality *and* the empty count, but ~300ms each, so scanning every field costs more than one paged fetch |
| `_summarize` needs the same vendor Content-Type as `_search` | 020 | **confirmed** — `application/json` is 415 |

`grouping` by a field returns one group per distinct value, with empties as a `''` group. That is the
metric fill rate cannot give: `code` returns one group per row (an identifier), `flagged` returns exactly
one (no information) — indistinguishable to a fill-rate scan. Not capped: 300 distinct codes, 300 groups.

## Pagination

| Claim | Probe | Needed by comfyui-fpt |
|---|---|---|
| The final `next` link claims more results but returns zero rows | 006 | **confirmed, worse — never absent** |
| `page[size]` is capped at 100 regardless of what is requested | 016 | **false** — 150 returns 150 |

Never trust `links.next` alone. Stop on an empty `data`, not on a missing `next`.

## Field types

Every field type has its own read, write, search and sort behaviour. They must be handled one type at a time;
there is no generic path.

| Claim | Probe | Needed by comfyui-fpt |
|---|---|---|
| Dotted paths through multi-entity fields | 016 | **reads no, filters yes** |
| Query fields need a batched follow-up call per result | — | no |
| TimeLog duration is stored in minutes but displayed in hours or days | — | no |
| Hours-per-day is a site setting that is not obviously exposed | — | no |
| Calculated and query fields cannot be written | — | no |

**Scope rule.** Mapping every field type is weeks of work and this repo grows only to serve a shipped consumer.
Probe the types the node writes and reads — text, entity, multi-entity, list/status, file and attachment.
Everything else stays a claim until something needs it.

## Statuses and icons

| Claim | Probe | Needed by comfyui-fpt |
|---|---|---|
| Status lists are site-wide; per-project usage is `valid_values` minus `hidden_values` when the field schema is read with `project_id` | 009 | yes |
| A status may be standard, custom with a standard icon, or custom with an uploaded icon | 010 | **confirmed** |
| Resolving the right icon for all three cases takes real code | 010 | **confirmed** |
| Icons must be cached, not refetched per render | 010 | yes |
| Icon entities cannot be created by a script/API user — needs a HumanUser session | — | only if we ever set icons |

Probe 010: three cases, keyed on `Icon.display_type`.

| display_type | who | how to render |
|---|---|---|
| `image_map` | 94 standard statuses | `image_map_key` (`icon_apr`) into a sprite. Sprite location still unknown — not under `/images/*`. |
| `image` | custom uploaded | `url` is a self-contained `data:image/png;base64` URI. Strip newlines. `image_data` holds the same bytes. |
| `html` | custom text badge | `html` holds the label. No image exists. |

`Status.icon` is an entity link, so it arrives under `relationships`. `bg_color` is comma-separated RGB and is
enough to render a badge with no icon at all — which is the fallback while the sprite is unresolved.

The node displays statuses, so this is in scope under the scope rule. Icons belong in the schema cache
alongside the field definitions, keyed per site, with the binary stored on disk rather than re-downloaded.

## Filters

| Claim | Probe | Outcome |
|---|---|---|
| Entity fields filter with a `{type, id}` hash: `[["entity", "is", {"type": "Asset", "id": 9}]]` | 014 | **confirmed** |
| Flat `filter[field]=value` params cannot express an entity hash | 014 | **confirmed** |
| Dotted paths through multi-entity fields cannot be **read** | 016 | **confirmed** — key silently absent |
| Dotted paths through multi-entity fields cannot be **filtered** | 016 | **false** — works, two hops included |
| `in` takes a list: `[["code", "in", ["a", "b"]]]` | 017 | **confirmed** |
| `in` takes a list of entity hashes: `[["entity", "in", [{"id": 1}]]]` | 017 | **confirmed, but the hash needs `type`** — `[{"id": N}]` and bare ints both 400 |
| `in` works on a dotted path too: `[["entity.Asset.code", "in", [...]]]` | 017 | **confirmed** |
| A substring operator exists for type-ahead over names | 017 | **confirmed** — `contains`, and it works through a dotted path |

Probe 017 also settles the safety question: an **unknown operator returns 400**, never a silent pass. That is
the opposite of a bogus `?fields` name (probe 004), which is dropped silently. A filter typo fails loudly;
a field typo reads as "no data".

Check `data_type` before building a dotted path to *read*: `entity` is safe, `multi_entity` silently returns
nothing. Filtering has no such restriction. To read multi-entity children, query the child entity separately.

`POST /entity/<type>/_search` needs `Content-Type: application/vnd+shotgun.api3_array+json`; `application/json`
is a 415.
