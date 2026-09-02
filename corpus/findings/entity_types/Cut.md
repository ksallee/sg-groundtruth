---
tags: [entity-type, cut, timecode, create, entity-field, multi-entity, status, list-field, schema, trap]
scope: api
measured: sandbox project; Cut holds 0 rows site-wide, so every row here was created by the probe
summary: An edit of a sequence or a reel, holding the clips that make it up.
verdict: A Cut stores an edit, it does not model one: no field is computed or validated, and `cut_items` is returned sorted by the item's display name rather than by `cut_order`.
---

# Cut

**Type** Schema name `Cut`, addressed at `/entity/cuts`. The slug is neither case nor plural sensitive,
but the underscore in a two-word name is:

```
GET /entity/cuts -> 200    GET /entity/Cut  -> 200    GET /entity/cutz -> 404 "Entity type 'cutz' does not exist."
GET /entity/cut  -> 200    GET /entity/Cuts -> 200
```

Project-scoped, and the endpoint is not: every read needs
`[["project", "is", {"type": "Project", "id": N}]]` of its own. On the probed site an unfiltered
`_search` on `/entity/cuts` and on `/entity/cut_items` returned 0 rows each, so every measurement here
comes from rows the probe created in one project.

**Identity** `code`, `data_type: text`, `mandatory: true`, `unique: false`. Nothing is unique: three
creates sending one `code` in one project all returned 201. `cached_display_name` is not a copy of `code`
but `code` plus the revision, and `revision_number` is a plain `number` the client maintains.

| `code`, `revision_number` sent | `cached_display_name` |
|---|---|
| `reel1`, `1` | `reel1 v001` |
| `reel1`, `2` | `reel1 v002` |
| `reel1`, omitted | `reel1` |

"The current cut" is a sort, not a lookup: filter on `code` and sort `-revision_number`, which returns
`null` last.

**Create** `POST /entity/cuts`, `Content-Type: application/json`. The schema's flags invert the contract
exactly as on Version and Shot (probe 012): the flagged `code` is optional, the unflagged `project` is
required.

| body sent | result |
|---|---|
| `{}` | 400 `API create() missing 'project' attribute: {}` |
| `{"code": "reel1"}` | 400 `API create() missing 'project' attribute: {"code" => "reel1"}` |
| `{"project": {"type": "Project", "id": N}}` | 201, `code` server-set to `New Cut <id>` |
| `{"project": {...}, "code": "reel1"}` | 201 |
| the identical body a second time | 201, a second Cut with the same `code` |
| `{"project": {...}, "code": ""}` | 400 code 104 `Create failed for [Cut]: Cannot set identifier field to empty. (Cut)` |
| `{"project": {...}, "code": ..., "fps": 24.0, "duration": 240, "timecode_start_text": "01:00:00:00"}` | 201, all stored as sent |

In a batch, `entity` is the schema name `Cut`; `"cuts"` is 400 `Invalid entity type` (`recipes/002`).

**Links** Read and written as `field_types/entity` and `field_types/multi_entity` describe.

| field | type | `valid_types` | what a client uses it for |
|---|---|---|---|
| `project` | entity | `['Project']` | required on create, and the filter on every read |
| `cut_items` | multi_entity | `['CutItem']` | the reverse of `CutItem.cut`, and not the running order. Editable, but an `add` of another Cut's item answered 200 and moved it, leaving the former Cut holding `[]`: link an item by writing `CutItem.cut` |
| `entity` | entity | `['Sequence', 'Scene', 'Episode', 'Reel']` | what the cut is of |
| `sg_scene` | entity | `['Scene']` | a second link to the same idea |
| `version` | entity | `['Version']` | the movie of the whole cut. `Version.cuts` fills in on the same write |
| `attachments` | multi_entity | `['Attachment']` | the source edit file |
| `notes`, `open_notes` | multi_entity | `['Note']` | `open_notes` is read only |
| `created_by`, `updated_by` | entity | `['HumanUser', 'ApiUser']` | read only |
| `image_source_entity` | entity | every site type | read only |

`valid_types` binds on one of the three link fields a client picks and not on the other two, with nothing
in the schema separating them (`field_types/entity`):

| field | `valid_types` | sent | result |
|---|---|---|---|
| `Cut.entity` | `['Sequence', 'Scene', 'Episode', 'Reel']` | Shot, Version | 200 each, read back as Shot and as Version |
| `Cut.sg_scene` | `['Scene']` | Shot | 200, reads back as a Shot |
| `Cut.version` | `['Version']` | Shot | 400 code 104 `Update failed for [Cut.version]: Version expected, got Shot` |

**Status** `sg_status_list`, `data_type: status_list`, with a `default_value` applied on create. Read a
project's usable set with `GET /schema/Cut/fields/sg_status_list?project_id=N` and subtract
`hidden_values` from `valid_values` yourself (probe 009): REST enforces only `valid_values`, and
`hidden_values` is not guaranteed to be a subset of it (`field_types/status_list`). The one `list` field
is `sg_cut_type`, read the same way. Both vocabularies are site configuration. On the probed site
`sg_status_list` returns `['ip', 'hld', 'apr', 'na']` with `default_value` `'ip'` and no
`hidden_values`, and `sg_cut_type` `['Boards', 'Assembly', 'Director', 'Final']` with no default.

**Traps**
- **The server computes nothing.** `duration` and the two timecode strings keep what was written: a Cut
  holding 6 items whose last frame is 647 still read `duration` 168 and `timecode_end_text`
  `'01:00:07:00'`, written when it held 3. The extent and every sum are the client's (`recipes/007`).
- **`cut_items` is not the running order.** It is returned sorted by the item's display name:
  `['aaa_last', 'sh010', 'sh020', 'sh030', 'sh030_gap', 'sh030_overlap']` against `cut_order`
  `1, 2, 3, 4, 5, 6` on the same six rows, as `Playlist.versions` does. Read the items with
  `POST /entity/cut_items/_search`, `[["cut", "is", {"type": "Cut", "id": N}]]`, `sort: "cut_order"`.
- **Deleting a Cut leaves its CutItems behind.** `DELETE /entity/cuts/<id>` answered 204 and the items
  survived with `cut` `null`, reachable only through `[["cut", "is", None]]`. Delete the items first.
- **The schema is not an exhaustive description of the response.** `GET /entity/cuts/<id>` returns
  `platform_id` and `platform_revision_id` under `attributes`, and neither appears in
  `/schema/Cut/fields`. A client that builds its field list from the schema alone will not ask for them,
  and one that validates a response against the schema will reject a legal row.
- `fps` is the only frame rate on Cut or CutItem, it is `null` until someone writes it, and a `float`
  reads back as the string `"24.0"` (`field_types/float`). Nothing on a CutItem points at it.
- Read only: `created_at`, `created_by`, `id`, `image_blur_hash`, `image_source_entity`, `open_notes`,
  `open_notes_count`, `updated_at`, `updated_by`.
