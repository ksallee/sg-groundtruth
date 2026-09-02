---
tags: [field-type, entity-field, write, filter, operator, dotted-field, trap]
scope: api
verdict: An entity link is a {type,id} hash under relationships, cleared only by null; valid_types is advisory on most fields and binding on a few, with nothing in the schema telling the two apart.
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

Whether `valid_types` binds is per field, and the schema does not mark which. Every entity field on
Version, each sent a type its own list omits, and every other case the type cards measured:

| field | `valid_types` | sent | result | measured in |
|---|---|---|---|---|
| `Version.client_approved_by` | `['HumanUser','ClientUser']` | Shot | 200, reads back as a Shot | here |
| `Version.entity` | 15 types | Task | 200, reads back as a Task | here |
| `Version.sg_task` | `['Task']` | Shot | 200, reads back as a Shot | here |
| `Version.source_clip` | `['SourceClip']` | Shot | 200, reads back as a Shot | here |
| `Version.user` | `['HumanUser','ApiUser','Group']` | Shot | 200, reads back as a Shot | here |
| `Shot.sg_sequence` | `['Sequence']` | Shot | 200, reads back as a Shot | `entity_types/Shot` |
| `Task.entity` | 8 types | Task | 200, reads back as a Task | `entity_types/Task` |
| `TimeLog.entity` | `['Task']` | Shot, Project | 201 each, stored as sent | `entity_types/TimeLog` |
| `Note.note_links`, multi_entity | 36 types | Project, HumanUser | 201 each, the link read back | `entity_types/Note` |
| `Cut.entity` | `['Sequence','Scene','Episode','Reel']` | Shot, Version | 200 each, read back as sent | `entity_types/Cut` |
| `Cut.sg_scene` | `['Scene']` | Shot | 200, reads back as a Shot | `entity_types/Cut` |
| `Version.project` | `['Project']` | Shot | 400 `Update failed for [Version.project]: Project expected, got Shot` | here |
| `Version.task_template` | `['TaskTemplate']` | Shot | 400 `Update failed for [Version.task_template]: TaskTemplate expected, got Shot` | here |
| `Sequence.episode` | `['Episode']` | Sequence | 400 `Update failed for [Sequence.episode]: Episode expected, got Sequence` | `entity_types/Sequence` |
| `TimeLog.user` | `['HumanUser']` | ApiUser, Project | 400 `Invalid field value, update failed [5 - Update failed for [TimeLog.user]: HumanUser expected, got ApiUser]` | `entity_types/TimeLog` |
| `Cut.version` | `['Version']` | Shot | 400 `Update failed for [Cut.version]: Version expected, got Shot` | `entity_types/Cut` |
| `CutItem.cut` | `['Cut']` | Shot | 400 `Cut expected, got Shot` | `entity_types/CutItem` |
| `CutItem.shot` | `['Shot']` | Version | 400 `Shot expected, got Version` | `entity_types/CutItem` |
| `CutItem.version` | `['Version']` | Shot | 400 `Version expected, got Shot` | `entity_types/CutItem` |
| `Version.created_by`, `updated_by` | `['HumanUser','ApiUser']` | Shot | 400 `API update() Version.created_by is editable on create only.` | here |
| `Version.image_source_entity` | 114 types | Task | 400 `API update() Version.image_source_entity is read only.` | here |

No property in the schema separates the two groups, and the obvious guesses do not survive the table.
The count of declared types does not predict it: `Version.source_clip` and `TimeLog.entity` each declare
one type and are advisory, while `Version.project` and `TimeLog.user` each declare one and bind. The `sg_`
prefix does not predict it either: `Version.source_clip` has no prefix and is advisory. Two fields on
one type can differ, as `TimeLog.entity` and `TimeLog.user` do.

A field that binds names the expected type, `<Expected> expected, got <Sent>`, at `code: 104` on the two
Version fields; the last two rows refuse for editability, not for type. Nothing in the schema separates
the groups: `sg_task`, `source_clip` and `task_template` each declare one valid type and only
`task_template` refused. One type does both: `TimeLog.entity` took a Project and `TimeLog.user`
refused one.

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

Three value shapes across the nine. Row counts against a 100-Version baseline, where `862` stands in for
the id of the Shot `sh010_0010` names:

| operator | value | matches |
|---|---|---|
| `is` | `{"type": "Shot", "id": 862}` | 3; `null` 0 |
| `is_not` | `{"type": "Shot", "id": 862}` | 97; `null` 100 |
| `in` | `[{"type": "Shot", "id": 862}]`, or a bare hash | 3 for one hash, 6 for two |
| `not_in` | `[{"type": "Shot", "id": 862}]`, or a bare hash | 97 for one hash, 94 for two |
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
- Validate the type against `valid_types` client-side, on every field. A client cannot predict which
  field will protect it, and an unenforced write stores nonsense at 200: `sg_task` (`['Task']`) took a
  Shot and read it back as a Shot.
- No project-consistency check. Pointing a sandbox Version at a Shot in another project returned 200 and
  read back linked, with nothing in the response flagging it. Compare projects before writing.
- A wrong `type` for a real id 400s here only because ids come from one site-wide sequence (250 shots
  862..1111 vs 250 assets 1226..3588, zero overlap), so the wrong table holds no such row. That is a lookup
  miss, not type validation.
- Reading `attributes` alone makes every entity link look absent, and `filter[]` needs the full
  `{type, id}`: `[{"id": N}]` and bare ints both 400 (probe 017), while a bad `?fields` name is silently
  dropped at 200 (probe 004).
