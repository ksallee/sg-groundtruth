# Known quirks

**Nothing in this file is a finding.** Every line is an operator claim, recorded before probing. Never code
against one. A job that depends on a claim has a gap: probe it, write the result under `corpus/findings/`,
and cite the finding instead.

How to read a table. The **Claim** column is what was believed, kept verbatim even after a probe proved it
wrong, because the wrong belief is itself worth knowing. The **Probe** column names the probe or finding that
settled it, or `none` where none has. The third column records what that probe found. A row with no probe stays
a claim however plausible it reads.

## Custom fields

| Claim | Probe | Outcome |
|---|---|---|
| Custom fields can be created over REST | 019 | **confirmed** |
| Not every type can: calculated and query fields are limited or impossible | 019 | **partly settled**: `color` and `image` 400 `{"data_type": ["data_type is not valid"]}`, `calculated` 500s. Query fields untested |
| All custom names are forced to an `sg_` prefix | 019 | **confirmed**, and it is added blind: `sg_foo` becomes `sg_sg_foo` |
| Display name maps to a computed programmatic name; `Foo (Bar)` becomes something like `sg_foo__bar_` | 019 | **confirmed**: `zzprobe 019 With (Parens)` becomes `sg_zzprobe_019_with__parens_`, and the name is absent from the response body. Take the last segment of `links.self` |
| Trashed fields cannot be listed | 019 | **confirmed**: `DELETE` returns 204 and the field vanishes from `/schema` |
| Creating a field can collide with a trashed field you cannot see | 019 | **confirmed**: recreating the same display name 400s `schema_field_create() failed` |
| A trashed field can be revived | 040 | **confirmed**: `POST /schema/<Type>/fields/<name>` with `{"revive": true}` is a 204. The call is in no documentation; the API names the parameter in a 400 |
| Reviving fails if the trashed field's type differs from the type you want | 040 | **confirmed in effect**: the revive succeeds but returns the field at its original type, and `data_type` is not editable. A `PUT` changing it at the top level is a 200 that does nothing |
| Recovery is: trash again, pick another programmatic name | 040 | **confirmed**: a different display name is a 201 |

Consequence: never POST and hope. A duplicate display name does not error, it creates `<name>_1`, so an
idempotent `ensure()` reads `/schema/<Type>/fields` and matches before it writes. The revive half is
settled by 040: there is no revive, the type is irrelevant, and a create 400 naming a retired field is
terminal over REST because no listing shows what was collided with. Encode the sequence once, in one
place, cited to 019 and 040.

**Probe fields are permanent litter.** Trashed names still collide and cannot be enumerated (019), so every
schema probe burns a name on the site forever. All probe fields use `sg_zzprobe_<nnn>_*` so they can never
collide with a name anyone would choose deliberately.

## Custom entities

| Claim | Probe | Outcome |
|---|---|---|
| Custom entities cannot be enabled over REST | none | unprobed: 008 only reads the schema, it never tries to enable a slot |
| They are addressed by programmatic name, `CustomEntity07` and so on | 008 | **confirmed** |
| Each site assigns those numbers differently: the number means nothing across sites | 008 | **confirmed**, and they are non-contiguous: 01-07, 19, 29 and 66 on the probed site |
| The real display name is in the schema | 008 | **confirmed**, under `name.value`, and it may hold a trailing space, so match trimmed |

Consequence: never hardcode a `CustomEntityNN`. Resolve display name to programmatic name through the schema
cache, per site. Presence in `/schema` is the enablement test (008): a disabled slot is absent.

## Statuses

| Claim | Probe | Outcome |
|---|---|---|
| Status lists cannot be mirrored project to project over REST | 009 | unsettled: 009 reads `hidden_values` per project and never tries to write one |
| The schema carries hidden values REST cannot control | 009 | **confirmed** that `hidden_values` is the only property `project_id` changes; `valid_values` is byte-identical at every scope |
| Setting a status hidden for an entity type breaks the frontend UI for it | none | **unverified**, and **not observable through the API** |

`field_types/status_list` settles the API half: `hidden_values` is **not enforced**. REST writes a
project-hidden status at 201 and reads it back. Whether doing so then breaks the web UI is an operator claim
and is **not observable through the API**; it needs a human looking at the browser. Until then a client should
subtract `hidden_values` and never offer a hidden code, treating the permissive API as a hazard rather than a
feature.

## Requests

| Claim | Probe | Outcome |
|---|---|---|
| Entity and multi-entity fields return array or hash form depending on request headers | 004 | **false as an `Accept` header** |

Probes 004 and 014: **true, but it is a request `Content-Type` on `POST _search`, not an `Accept` header on
`GET`.** Those vendor types sent as `Accept` on a GET return 406; `POST /entity/<type>/_search` rejects
`application/json` with 415 and requires `application/vnd+shotgun.api3_array+json` or `...api3_hash+json`.
Responses are unaffected: entity fields are always returned under `relationships`.

## Projects

| Claim | Probe | Outcome |
|---|---|---|
| A project picker filters on `[["sg_status", "is", "Active"]]` | 018 | **false**: null on 15 of 22 projects here, including newly created ones |
| `is_template` / `is_demo` / `archived` identify projects a human would not publish into | 018 | **confirmed** |

`sg_status` has no `display_values` and is never set automatically. Filter the checkboxes; leave status alone.

## Summaries

| Claim | Probe | Outcome |
|---|---|---|
| Summarize calls are cheap and describe a field's values | 020 | **half true**: one call gives cardinality *and* the empty count, but at ~300ms each, scanning every field costs more than one paged fetch |
| `_summarize` needs the same vendor Content-Type as `_search` | 020 | **confirmed**: `application/json` is 415 |

`grouping` by a field returns one group per distinct value, with empties as a `''` group. That is the metric
fill rate cannot give: `code` returns one group per row (an identifier), `flagged` returns exactly one (no
information), and a fill-rate scan cannot tell the two apart. Not capped: 300 distinct codes, 300 groups.

## Pagination

| Claim | Probe | Outcome |
|---|---|---|
| The final `next` link claims more results but returns zero rows | 006 | **confirmed, and worse: never absent** |
| `page[size]` is capped at 100 regardless of what is requested | 016 | **false**: 150 returns 150 |

Never trust `links.next` alone. Stop on an empty `data`, not on a missing `next`.

## Field types

Every field type has its own read, write, search and sort behaviour. They must be handled one type at a time;
there is no generic path.

| Claim | Probe | Outcome |
|---|---|---|
| Dotted paths through multi-entity fields | 016 | **reads no, filters yes** |
| Query fields need a batched follow-up call per result | `field_types/summary` | **false for reads**: the rollup value is returned inline under `attributes`. The follow-up is needed only to filter or sort, since both fail, and `/schema` exposes the rollup's own `query` so it can be re-run |
| TimeLog duration is stored in minutes but displayed in hours or days | `field_types/duration` | **confirmed for storage**: a `duration` is a bare integer of minutes |
| Hours-per-day is a site setting that is not obviously exposed | `field_types/duration` | **confirmed**: no endpoint returns it. Print minutes, or take hours-per-day as a configured input |
| Calculated and query fields cannot be written | `field_types/calculated`, `field_types/summary`, `field_types/pivot_column` | **confirmed**: `is read only` on all three, and `API update() of data type 'summary' not supported in API` even where `editable` is true |

**Scope rule.** This repo grows only to serve a shipped consumer. `corpus/findings/field_types/` holds 19
types, one reference card each. A type without a file there stays a claim until something needs it.

## Statuses and icons

| Claim | Probe | In scope |
|---|---|---|
| Status lists are site-wide; per-project usage is `valid_values` minus `hidden_values` when the field schema is read with `project_id` | 009 | yes |
| A status may be standard, custom with a standard icon, or custom with an uploaded icon | 010 | **confirmed** |
| Resolving the right icon for all three cases takes real code | 010 | **confirmed** |
| Icons must be cached, not refetched per render | 010 | yes |
| Icon entities cannot be created by a script/API user; it needs a HumanUser session | none | only if we ever set icons |

Probe 010: three cases, keyed on `Icon.display_type`.

| display_type | who | how to render |
|---|---|---|
| `image_map` | 94 standard statuses | `image_map_key` (`icon_apr`) into a sprite. Sprite location still unknown, and not under `/images/*` |
| `image` | custom uploaded | `url` is a self-contained `data:image/png;base64` URI. Strip newlines. `image_data` holds the same bytes |
| `html` | custom text badge | `html` holds the label. No image exists |

`Status.icon` is an entity link, so it is returned under `relationships`. `bg_color` is comma-separated RGB
and is enough to render a badge with no icon at all, which is the fallback while the sprite is unresolved.

A client that displays statuses needs these, so they are in scope under the scope rule. Icons belong in the
schema cache alongside the field definitions, keyed per site, with the binary stored on disk rather than
re-downloaded.

## Filters

| Claim | Probe | Outcome |
|---|---|---|
| Entity fields filter with a `{type, id}` hash: `[["entity", "is", {"type": "Asset", "id": 9}]]` | 014 | **confirmed** |
| Flat `filter[field]=value` params cannot express an entity hash | 014 | **confirmed** |
| Dotted paths through multi-entity fields cannot be **read** | 016 | **confirmed**: the key is silently absent |
| Dotted paths through multi-entity fields cannot be **filtered** | 016 | **false**: it works, two hops included |
| `in` takes a list: `[["code", "in", ["a", "b"]]]` | 017 | **confirmed** |
| `in` takes a list of entity hashes: `[["entity", "in", [{"id": 1}]]]` | 017 | **confirmed, but the hash needs `type`**: `[{"id": N}]` and bare ints both 400 |
| `in` works on a dotted path too: `[["entity.Asset.code", "in", [...]]]` | 017 | **confirmed** |
| A substring operator exists for type-ahead over names | 017 | **confirmed**: `contains`, and it works through a dotted path |

Probe 017 also settles the safety question. An **unknown operator returns 400** with the valid list, never a
silent pass. A bogus `?fields` name is dropped silently instead (probe 004). A filter typo fails loudly; a
field typo reads as "no data".

Check `data_type` before building a dotted path to *read*: `entity` is safe, `multi_entity` silently returns
nothing. Filtering has no such restriction. To read multi-entity children, query the child entity separately.

`POST /entity/<type>/_search` needs `Content-Type: application/vnd+shotgun.api3_array+json`; `application/json`
is a 415.

## Media resolution

Operator knowledge, plus public docs. Unverified until a site with a real publish history can be probed:
probe 021 measured what this site can deliver, not what the model is.

| Claim | Source | Status |
|---|---|---|
| A Version's best media is its PublishedFiles, then `sg_path_to_movie`/`sg_path_to_frames`, then the upload | operator | plausible, **untested**. See below |
| `PublishedFile.path` carries the LocalStorage join already done | probe 021 | **confirmed**: `local_path_mac/windows/linux` are server-filled |
| `sg_path_to_frames` uses printf padding, `foo.%04d.jpg` | operator + docs | **partly true, and not the only form** |
| Studios that use Toolkit have PublishedFiles; many studios have Versions only | operator | plausible, untested |

**Why probe 021 could not test the PublishedFile tier.** Two separate causes, and only one is about Flow PT:

- *Flow PT*: on this site the Image, Rendered Image, Texture and USD PublishedFiles hold **no `path` at all**,
  and `Version.published_files` is filled on 2 of 53 Versions. That is real data about the site.
- *Not Flow PT*: the Movie paths that do exist point at files the operator has since **deleted from disk**.
  A missing file says nothing about the API. Do not read probe 021 as evidence that Flow PT paths are unreliable.

Toolkit's `register_publish` is what populates this properly. It can reportedly be lifted out of `tk-core` and
run with just a storage root, no Toolkit install, as done before at a previous studio. That is the route to
real test data. `tk-core` is off limits to read here (clean room), so this stays a note, not a plan.

**Frame sequence notation is not one format.** RV and the Flow PT integrations accept printf padding (`%04d`,
and other widths), and also the Shake-style `#` and `@` forms. The field is free text with no validation, so a
client must recognise several notations and must not assume `%04d`. Both path fields take **absolute** paths,
so a single value cannot resolve on both Windows and macOS. `PublishedFile.path` is the exception: it holds
all three.
