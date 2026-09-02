---
tags: [field-type, multi-entity, entity-field, write, filter, operator, dotted-field, trap]
scope: api
verdict: A bare list replaces the whole link set, but {"multi_entity_update_mode": "add"|"remove"|"set", "value": [...]} adds and removes in place; the field never reads null and null 400s.
---

# multi_entity

**Data type** `multi_entity`, probed on `Version.sg_ai_generated_from` (stock, editable,
`valid_types: ["Version"]`). Version has 10: `cuts, notes, open_notes, playlists, published_files,
sg_ai_generated_from, sg_deliveries, tags, tasks, version_sg_ai_generated_from_versions`, the last a
reverse field of `sg_ai_generated_from`. `valid_types` is under `properties`, not at the top level, and
holds one type on each (`tasks: ["Task"]`, `playlists: ["Playlist"]`, `notes: ["Note"]`), matching the
one-element rule creation enforces (probe 019); single `entity` is the opposite, `Version.entity`
listing 15. `attachment_links` is a field on `Attachment`, not on `Version`: filter it with
`[["attachment_links", "is", {"type": "Version", "id": N}]]` from `/entity/attachments/_search`
(probe 014).

**Read** Under `relationships`, never `attributes`, as `{data: [...], links: {self}}`. Each element is
`{id, name, type}`, where `name` is the target's display name, already resolved.

```
relationships.sg_ai_generated_from = {"data": [{"id": 26332, "name": "zzprobe_..._target_a",
  "type": "Version"}, {"id": 26333, "name": "zzprobe_..._target_b", "type": "Version"}],
  "links": {"self": "/api/v1/entity/versions/26334/relationships/sg_ai_generated_from"}}
unset -> {"data": [], "links": {...}}     <- empty list. never null, never an absent key
```

**Write** `PUT /entity/versions/{id}` with `Content-Type: application/json`. The field value is either a
bare list of `{type,id}` hashes or the wrapper `{"multi_entity_update_mode": "add"|"remove"|"set",
"value": [{type,id}]}`. Starting from `[A]`:

| field value sent | result |
|---|---|
| bare `[B]` | 200, `[B]`. `A` is gone; a bare list is a replace |
| `add [B]` | 200, `[A, B]` |
| `add [A]` | 200, `[A]`, deduped |
| `add []` | 200, `[A]` |
| `remove [A]` | 200, `[]` |
| `remove [B]` | 200, `[A]` |
| `set [B]` | 200, `[B]` |
| `?multi_entity_update_mode=add` in the query string | 200, list replaced |
| `?options[multi_entity_update_modes][field]=add` in the query string | 200, list replaced |

Value shapes, on the bare-list form:

| sent | result |
|---|---|
| `[{type,id}, {type,id}]` | 200, both |
| the same `{type,id}` twice | 200, stored once |
| `[]` | 200, `[]` |
| `[A, B]` bare ints | 400 `API update() invalid/missing entity hash: 26332` |
| `{type,id}` bare hash | 400 `API update() invalid/missing string 'multi_entity_update_mode'` |
| `[{"id": A}]` | 400 `API update() invalid/missing entity hash string 'type': {"id" => 26332} Valid entity types: ["ActionMenuItem", ... 113 types listed in full ...]` |
| `[Version, Task]` mixed | 400 `Update failed for [Version.sg_ai_generated_from]: Value is not legal.` |
| `[{type:Version,id:99999999}]` | 400 same `Value is not legal.` |

A dead id and a forbidden type are indistinguishable. `value` is the only accepted payload key: `values`,
`entities`, `data` and inline `type`/`id` all 400 with `invalid/missing array of entity hashes 'value'`,
and an unknown mode is rejected. There is no relationship endpoint: `GET` on
`relationships/sg_ai_generated_from` returns 200, while `POST` and `DELETE` there, and
`PATCH /entity/versions/{id}`, all 404.

**Clear**

| sent | result |
|---|---|
| `[]` | cleared |
| `{"multi_entity_update_mode": "set", "value": []}` | cleared |
| `null` | 400 `API update() Version.sg_ai_generated_from expected [Array, Hash] data type(s) but got NilClass: nil` |
| `""` | 400 `… expected [Array, Hash] data type(s) but got String: ""` |
| `0` | 400 `… expected [Array, Hash] data type(s) but got Integer: 0` |
| key omitted from the PUT | unchanged |

A cleared field reads back `{"data": []}`, identical to one never set; no round trip separates them.

**Filter** From a bogus operator, verbatim:

```
"API read() Version.tasks's 'multi_entity' data type doesn't support 'definitely_not_an_operator'
 'relation'"  source: {"Version.tasks": " ... Value: {"path" => "tasks", "relation" => ...}
 Valid relations: ["is", "is_not", "name_contains", "name_not_contains", "name_is", "type_is",
 "type_is_not", "in", "not_in"]"}
```

Nine against text's eight, trading `contains/not_contains/starts_with/ends_with` for the five `name_*`
and `type_*`. Four rows: `AB` links both targets, `A_only` and `B_only` link one, `empty` links nothing.
`A` and `B` below stand for those two targets, each sent as `{"type": "Version", "id": <id>}`.

| operator | value | matches |
|---|---|---|
| `is` | `A` | `AB A_only` |
| `is` | `None` | `empty` |
| `is` | `{"type": "Version", "id": 99999999}` | none |
| `is` | `[A, B]` | 400 `API read() 'is' 'relation' expects a 1-element array: [...]` |
| `is_not` | `A` | `B_only empty` |
| `is_not` | `None` | `AB A_only B_only` |
| `in` | `[A]` | `AB A_only` |
| `in` | `[A, B]` | `AB A_only B_only` |
| `in` | `[]` | 400 `API read() 'in' 'relation' expects at least a 1-element array: []` |
| `in` | `[26342]`, a bare id | 400 `invalid/missing entity hash: 26342` |
| `in` | `[{"id": <A>}]` | 400 missing `'type'` |
| `not_in` | `[A]` | `B_only empty` |
| `not_in` | `[A, B]` | `empty` |
| `type_is` | `"Version"` | `AB A_only B_only` |
| `type_is_not` | `"Version"` | `empty` |
| `name_is` | `<A's code>` | `AB A_only` |
| `name_contains` | `"_target_a"` | `AB A_only` |
| `name_contains` | `"ZZZNOPE"` | none |
| `name_not_contains` | not measured | not measured |

Two filter rows intersect, and a dotted path reaches the target's own fields:

| filter | matches |
|---|---|
| `is A` plus `is B`, as two filter rows | `AB` |
| `sg_ai_generated_from.Version.code is <A's code>` | `AB A_only` |
| `sg_ai_generated_from.Version.code is ZZZNOPE` | none |

**Traps**
- Both incremental spellings that live in the query string return 200 having **silently replaced** the
  list. The loss is a success response, not an error; send the mode in the body.
- A bare list replaces, so an append coded as read-then-PUT loses any link a concurrent writer added
  between the two calls. Use the `multi_entity_update_mode` wrapper, not read-modify-write.
- `in [X]` means "links any of X" and `not_in [X]` means "links none of X", so it matches empty rows, as
  does `is_not`. "Links all of X" has no operator: repeat `is` once per entity, as separate filter rows.
- `in` with only unresolvable ids degenerates: `in [{type:Version,id:99999999}]` returns the rows linking
  nothing rather than zero rows, so that negative control lies. Mixed, `in [A, 99999999]` returns A's rows.
- A dotted path through this field reads back nothing: 200, key absent from `attributes`, in `GET ?fields`
  and in `_search` alike, while the identical path filters correctly (probe 016). To read the far side,
  query the child entity filtered by the parent.
- Read order is not insertion order (adding B then A read back A then B), so never treat it as a sequence.
