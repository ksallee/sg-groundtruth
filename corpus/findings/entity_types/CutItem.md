---
tags: [entity-type, cut, timecode, create, entity-field, filter, operator, dotted-field, schema, trap]
scope: api
measured: sandbox project; CutItem holds 0 rows site-wide, so every row here was created by the probe
summary: One clip in a Cut, with its position in the edit and in its source.
verdict: Nothing on a CutItem is unique and `code` repeats across Cuts, so an id found by a code search may sit on another Cut: check `cut` before every update or the write lands on the wrong edit.
---

# CutItem

**Type** Schema name `CutItem`, addressed at `/entity/cut_items`. The slug is neither case nor plural
sensitive, but the underscore is part of the name:

```
GET /entity/cut_items -> 200    GET /entity/CutItem   -> 200
GET /entity/cut_item  -> 200    GET /entity/cutitems  -> 404 "Entity type 'cutitems' does not exist."
```

Project-scoped, and `project` is required on create even when `cut` is sent. One item is one clip in one
Cut (`entity_types/Cut`); the build-and-read loop is `recipes/007`. On the probed site an unfiltered
`_search` returned 0 rows, so every measurement here comes from rows the probe created.

**Identity** `code`, `data_type: text`, `mandatory: true`, `unique: false`, holding the clip name, and
`cached_display_name` mirrors it. Nothing on the type is unique: two items created in one Cut with one
`code` both returned 201, and one `code` in two Cuts is ordinary. `id` is the only enforced identifier.

**Create** `POST /entity/cut_items`, `Content-Type: application/json`.

| body sent | result |
|---|---|
| `{"code": "sh010", "cut": {"type": "Cut", "id": N}}` | 400 `API create() missing 'project' attribute: {"code" => "sh010", "cut" => {"type" => "Cut", "id" => 19}}` |
| `{"project": {"type": "Project", "id": N}}` | 201, `code` server-set to `New Cut Item <id>`, every other field `null` |
| `{"project": {...}, "code": "sh010"}` | 201, and `cut` `null`: an item needs no Cut |
| the identical body a second time, in the same Cut | 201, a second item with the same `code` |
| `{"project": {...}, "code": ""}` | 400 code 104 `Create failed for [CutItem]: Cannot set identifier field to empty. (CutItem)` |
| the full timeline payload below | 201, every number and string stored as sent |

In a batch, `entity` is the schema name `CutItem`: `"cut_item"` is 400
`Invalid entity type: entity type [cut_item] does not exist.` and `"CutItems"` the same with
`[CutItems]`.

**Timeline** Six `number` fields of frames and four `text` fields of `HH:MM:SS:FF`, on two axes, the cut
and the source. The server fills none of them and relates none of them. Neither type has a field of data
type `timecode`, so the millisecond integer of `field_types/timecode` is not in play, and the rate is
`Cut.fps`, which nothing here points at.

| field | data type | axis |
|---|---|---|
| `cut_order` | number | the item's rank in the cut |
| `edit_in`, `edit_out` | number | frames, position in the cut |
| `cut_item_in`, `cut_item_out` | number | frames, position in the source |
| `cut_item_duration` | number | frames, length. Still `null` after `edit_in` and `edit_out` are written |
| `timecode_edit_in_text`, `timecode_edit_out_text` | text | the same position in the cut |
| `timecode_cut_item_in_text`, `timecode_cut_item_out_text` | text | the same position in the source |

| written | result |
|---|---|
| `edit_in` 100 with `edit_out` 50, or both frames negative | 200, stored as sent |
| a second item with the same `cut_order`, or `cut_order` `null` | 200 |
| `"banana"` in a timecode field, or an out timecode before its in | 200, stored as sent |
| `""` in a timecode field | 200, stored as `null` (`field_types/text`) |

A gap and an overlap between two items are not stored: both are the difference between one item's
`edit_out` and the next item's `edit_in`, computed by the reader (`recipes/007`).

**Links**

| field | type | `valid_types` | binding |
|---|---|---|---|
| `project` | entity | `['Project']` | required on create |
| `cut` | entity | `['Cut']` | yes: a Shot is 400 `Update failed for [CutItem.cut]: Cut expected, got Shot` |
| `shot` | entity | `['Shot']` | yes: a Version is 400 `Update failed for [CutItem.shot]: Shot expected, got Version` |
| `version` | entity | `['Version']` | yes: a Shot is 400 `Update failed for [CutItem.version]: Version expected, got Shot` |
| `tags` | multi_entity | `['Tag']` | |
| `created_by`, `updated_by` | entity | `['HumanUser', 'ApiUser']` | read only |
| `image_source_entity` | entity | every site type | read only |

All three links a client sets bind, the minority behaviour for `entity` fields (`field_types/entity`).
`Cut.cut_items` is the reverse of `cut`, and since `cut` is single-valued an `add` there re-parents.

**Status** None. `GET /schema/CutItem/fields/sg_status_list` is 404
`Field 'CutItem.sg_status_list' does not exist.`, and the type has no field of `data_type: status_list`
and no `list` field at all. A cut's status is on the Cut.

**Filter** `POST /entity/cut_items/_search`,
`Content-Type: application/vnd+shotgun.api3_array+json`. Five items in one project: `order1`, `order2`,
`order2b` and `ordernull` on one Cut with `cut_order` `1`, `2`, `2` and `null`, plus `nocut` with no Cut.
`cut_order` answers the seven `number` relations, `cut` the nine `entity` ones (probe 017).

| operator | value | matches |
|---|---|---|
| `is` | `2` | `order2 order2b` |
| `is` | `None` | `ordernull` |
| `is_not` | `2` | `order1 ordernull nocut` |
| `is_not` | `None` | `order1 order2 order2b nocut` |
| `greater_than` | `1` | `order2 order2b` |
| `less_than` | `2` | `order1 nocut` |
| `between` | `[1, 2]` | `order1 order2 order2b nocut` |
| `in` | `[1, 2]` | `order1 order2 order2b nocut` |
| `not_in` | `[1]` | `order2 order2b ordernull` |
| `contains` | `"1"` | 400 `API read() CutItem.cut_order's 'number' data type doesn't support 'contains' 'relation'` |
| `cut is` | `{"type": "Cut", "id": N}` | `order1 order2 order2b ordernull` |
| `cut is` | `None` | `nocut` |
| `cut is_not` | `{"type": "Cut", "id": N}` | `nocut`, and every item of every other Cut |
| `cut is_not` | `None` | the four, and every item of every other Cut |
| `cut in` | `[{"type": "Cut", "id": N}]` | the four |
| `cut not_in` | `[{"type": "Cut", "id": N}]` | `nocut`, and every item of every other Cut |
| `cut type_is` | `"Cut"` | every item that has a Cut |
| `cut type_is_not` | `"Cut"` | `nocut` |
| `cut name_is`, `cut name_contains` | the Cut's `cached_display_name` | the four |
| `cut.Cut.code is`, `cut.Cut.code contains` | the Cut's `code` | the four |

`cut.Cut.id` also reads back in `fields`, unlike a dotted path through a multi_entity field (probe 016).

**Traps**
- **An id does not say which Cut a row is on, and `code` repeats across Cuts.** A search on
  `[["code", "is", "sh010"]]` returned items `(46, cut 19)` and `(53, cut 20)`. A blind
  `PUT /entity/cut_items/53` with no `cut` key answered 200, left `cut` at 20, and overwrote the other
  Cut's item. Deciding update-versus-create on "does it have an id" is the data-loss path: read the
  candidates filtered on `cut`, or ask for `cut.Cut.id` and drop every id that does not match.
- **Sending `cut` in an update moves the item** to that Cut at 200, and `Cut.cut_items` with
  `{"multi_entity_update_mode": "add"}` on the other side does the same, leaving the previous Cut
  holding `[]`.
- **`cut_order` is not a sequence the server maintains.** It is neither unique nor mandatory nor
  contiguous, `null` sorts last in both directions, and rows with an equal `cut_order` break the tie by
  `id`. It is also what a recut changes, so it is not a key: pair items across two edits on `code` plus
  its occurrence, scoped to the Cut (`recipes/007`).
- Read only: `created_at`, `created_by`, `id`, `image_blur_hash`, `image_source_entity`, `updated_at`,
  `updated_by`.
