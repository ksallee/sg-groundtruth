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

Probe 004: `api3_array+json` and `api3_hash+json` both return 406. REST always renders entity and multi-entity
fields under `relationships` as `{data, links}`, with no negotiation. The array/hash distinction belongs to
`shotgun_api3`, not to REST — relevant to the setup path only.

## Pagination

| Claim | Probe | Needed by comfyui-fpt |
|---|---|---|
| The final `next` link claims more results but returns zero rows | 006 | yes — enumeration |
| `page[size]` is capped at 100 regardless of what is requested | 005 | **confirmed** |

Never trust `links.next` alone. Stop on an empty `data`, not on a missing `next`.

## Field types

Every field type has its own read, write, search and sort behaviour. They must be handled one type at a time;
there is no generic path.

| Claim | Probe | Needed by comfyui-fpt |
|---|---|---|
| Dotted reads differ for single vs multi-entity targets — `sg_version.Version.code` vs `sg_version.Version.entity` | — | yes, before Phase 2 |
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
| A status may be standard, custom with a standard icon, or custom with an uploaded icon | 010 | yes |
| Resolving the right icon for all three cases takes real code | 010 | yes |
| Icons must be cached, not refetched per render | 010 | yes |

The node displays statuses, so this is in scope under the scope rule. Icons belong in the schema cache
alongside the field definitions, keyed per site, with the binary stored on disk rather than re-downloaded.
