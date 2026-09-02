---
tags: [field-type, entity-field, write, filter, operator, dotted-field, trap]
scope: api
verdict: An entity link is a {type,id} hash under relationships, cleared only by null; valid_types binds on two of Version's seven editable entity fields, so the API will point sg_task at a Shot.
---

# entity

**Data type** `entity`, probed on stock `Version` fields. On the probed site 10 of Version's 71 fields
are `entity`: seven editable, plus `created_by`, `updated_by` and `image_source_entity`, which are not.

**Read** Under `relationships`, never `attributes`. `?fields=entity` puts nothing in `attributes`, so a
reader that only walks `attributes` sees every link as absent (probe 003, probe 004):

```json
"relationships": {"entity": {
  "data":  {"id": 1230, "name": "charA", "type": "Asset"},
  "links": {"self":    "/api/v1/entity/versions/17055/relationships/entity",
            "related": "/api/v1/entity/assets/1230"}}}
```

`data` is `null` when unlinked. `name` is the linked row's display name, free: no second call to render a
picker. A dotted path reads back on a single link (unlike multi_entity, probe 016), but it is typed:

| row | `attributes` |
|---|---|
| links an Asset | `{"code": "charA_art_v001", "entity.Shot.code": null}` |
| links a Shot | `{"code": "sh010_0010_comp_v001", "entity.Shot.code": "sh010_0010"}` |

**Write** `PUT /entity/versions/<id>` with a `{"type": ..., "id": ...}` hash; identical shape on create
(probe 012).

| sent | result |
|---|---|
| `{"type": "Shot", "id": A}` | 200, reads back `{"id":7478,"name":"zzprobe_entity_a","type":"Shot"}` |
| `7479` (bare int) | 400 `API update() Version.entity expected [Hash, ActiveSupport::HashWithIndifferentAccess, ActionDispatch::Http::Parameters, ActionDispatch::Http::ParamsHashWithIndifferentAccess, NilClass] data type(s) but got Integer: 7479` |
| `{"id": 7479}` (no type) | 400 `API update() invalid/missing entity hash string 'type': {"id" => 7479} Valid entity types: ["ActionMenuItem", "ApiUser", ... all 113 site entity types listed in full ...]` |
| `{"type": "Asset", "id": <a real Shot id>}` | 400 `Update failed for [Version.entity]: Value is not legal.` |
| `{"type": "Shot", "id": 99999999}` | 400 `Update failed for [Version.entity]: Value is not legal.` |
| a Shot in another project | 200, linked; no project-consistency check |

`Value is not legal` is the only signal for both a wrong `type` and a missing id, and it has no `source`
and no `detail`. Every failed write left the previous value intact: no partial update.

Whether `valid_types` binds is per field. Every entity field on Version, each sent a type its own list
omits:

| field | `valid_types` | sent | result |
|---|---|---|---|
| `client_approved_by` | `['HumanUser','ClientUser']` | Shot | 200, reads back as a Shot |
| `entity` | 15 types | Task | 200, reads back as a Task |
| `sg_task` | `['Task']` | Shot | 200, reads back as a Shot |
| `source_clip` | `['SourceClip']` | Shot | 200, reads back as a Shot |
| `user` | `['HumanUser','ApiUser','Group']` | Shot | 200, reads back as a Shot |
| `project` | `['Project']` | Shot | 400 `Update failed for [Version.project]: Project expected, got Shot` |
| `task_template` | `['TaskTemplate']` | Shot | 400 `Update failed for [Version.task_template]: TaskTemplate expected, got Shot` |
| `created_by`, `updated_by` | `['HumanUser','ApiUser']` | Shot | 400 `API update() Version.created_by is editable on create only.` |
| `image_source_entity` | 114 types | Task | 400 `API update() Version.image_source_entity is read only.` |

The two that bind name the expected type and answer `code: 104`; the five that do not are indistinguishable
in the schema from the two that do. One valid type is not the rule: `sg_task` and `source_clip` list one
each and took a Shot.

**Clear**

| sent | result |
|---|---|
| `null` | cleared, reads back `null` |
| `{}` | 400 `invalid/missing entity hash string 'type': {} Valid entity types: [... 113 ...]` |
| `""` | 400 `... expected [Hash, ... NilClass] data type(s) but got String: ""` |
| `[]` | 400 `... expected [Hash, ... NilClass] data type(s) but got Array: []` |
| `{"type": "Shot", "id": null}` | 400 `invalid/missing entity hash integer 'id': {"type" => "Shot", "id" => nil}` |

There is no "empty entity" value, and a cleared link is findable: `["entity", "is", None]` matches the row.

**Filter** A bogus relation makes the API name the whole vocabulary (probe 017), here verbatim from
`errors[0].source["Version.entity"]`:

```
Valid relations: ["is", "is_not", "name_contains", "name_not_contains", "name_is", "type_is", "type_is_not", "in", "not_in"]
```

Three value shapes across the nine. Row counts against a 100-Version baseline:

| operator | value shape | matches |
|---|---|---|
| `is` | `{type,id}` | 3; `null` 0 |
| `is_not` | `{type,id}` | 97; `null` 100 |
| `in` | `{type,id}`, or a list of them | 3 for one hash, 6 for two |
| `not_in` | `{type,id}`, or a list of them | 97 for one hash, 94 for two |
| `type_is` | `"Shot"` | 99; a name string 0; `null` 0 |
| `type_is_not` | `"Shot"` | 1; a name string 100; `null` 100 |
| `name_is` | `"sh010_0010"` | 3; a type string 0 |
| `name_contains` | `"sh010_0010"` | 3; a type string 0 |
| `name_not_contains` | `"sh010_0010"` | 97; a type string 100 |

Every shape outside that column 400s: `[{"id": N}]` and bare ints throughout, a list for `is`/`is_not`, a
hash for `type_*` and `name_*`, `null` for the `name_*` three.

Dotted paths work, and every negative control returns 0 rather than the baseline:

| filter | rows |
|---|---|
| `entity.Shot.code is 'sh010_0010'` | 3 |
| `entity.Shot.code in [2 real codes]` | 6 |
| `entity.Shot.code contains '010_00'` | 21 |
| `entity.Shot.code is 'ZZZNOPE'` | 0 |
| `entity is {Shot, 99999999}` | 0 |
| `entity is None` | 0 (all 100 linked here) |

**Traps**
- `valid_types` is documentation on five of the seven editable fields and a constraint on the other two,
  with nothing in the schema separating them. Validate against `valid_types` client-side or store
  nonsense: `sg_task` (`['Task']`) took a Shot at 200 and read it back as a Shot.
- No project-consistency check. Pointing a sandbox Version at a Shot in another project returned 200 and
  read back linked, with nothing in the response flagging it. Compare projects before writing.
- A wrong `type` for a real id 400s here only because ids come from one site-wide sequence (250 shots
  862..1111 vs 250 assets 1226..3588, zero overlap), so the wrong table holds no such row. That is a lookup
  miss, not type validation.
- Reading `attributes` alone makes every entity link look absent, and `filter[]` needs the full
  `{type, id}`: `[{"id": N}]` and bare ints both 400 (probe 017), while a bad `?fields` name is silently
  dropped at 200 (probe 004).
