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

| Claim | Probe |
|---|---|
| Entity and multi-entity fields return array or hash form depending on request headers | 004 |

Suspected content negotiation on `Accept` (an `api3_array` vs `api3_hash` variant). Unconfirmed — 004 decides,
and the client then picks one form and never varies it.
