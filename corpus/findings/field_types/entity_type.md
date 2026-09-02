---
tags: [field-type, entity-field, schema, write, filter, operator, custom-entity, trap]
scope: api
summary: The name of an entity type, held as a string rather than as a link.
verdict: An entity_type field is a bare schema-name string in attributes, validated on write against 290 built-in type names but not against the site's enabled ones, and filtered only by is/is_not/in/not_in.
---

# entity_type

**Data type** `entity_type`. On the probed site five fields have it, all named `entity_type`, found by
sweeping `/schema/<Type>/fields` across the 114 types in `/schema`.

| field | editable |
|---|---|
| `ActionMenuItem.entity_type` | yes |
| `Page.entity_type` | no |
| `PermissionRuleSet.entity_type` | no |
| `Step.entity_type` | no |
| `TaskTemplate.entity_type` | no |

`properties` is `['default_value', 'summary_default']` on all five, with `default_value: null`. No
`valid_values`, no `valid_types`: the legal set exists only in the write error below.

**Read** A bare string in `attributes`, never in `relationships`. The value is the **schema name**
(`Shot`), not the REST path slug (`shots`), so a client building a URL from it must slug the name itself.

```json
{"type": "Step", "attributes": {"code": "Online", "entity_type": "Shot"}, "relationships": {}, "id": 2}
```

On the probed site, four of the five hold rows:

| endpoint | rows | distinct | values |
|---|---|---|---|
| `/entity/steps` | 35 | 3 | `Asset` 13, `Shot` 12, `Level` 10 |
| `/entity/task_templates` | 20 | 4 | `Asset` 11, `Shot` 6, `Level` 2, `Sequence` 1 |
| `/entity/permission_rule_sets` | 12 | 6 | `HumanUser` 5, `PermissionRuleSet.HumanUser` 3, three more at 1 |
| `/entity/pages` | 500 | 60 | `null` 38, `Asset` 28, `Task` 27, `Version` 27, 56 more |
| `/entity/action_menu_items` | 0 | 0 | |

Two of those values are not types a client can query. `PermissionRuleSet.HumanUser` is a dotted composite,
and `Page.entity_type` reaches `DisplayColumn`, which is in the write error's legal set but absent from
`/schema` and has no `/entity/` endpoint. Resolve a read value against `/schema` before dereferencing it.

**Write** `PUT /entity/action_menu_items/<id>` with a plain string. Validated against a fixed list of 290
built-in type names, quoted in full in every rejection.

| sent | result |
|---|---|
| `"Shot"` | 200, reads back `"Shot"` |
| `"shot"`, `"SHOT"` | 400 `Update failed for [ActionMenuItem.entity_type]: 'shot' is not a valid entity type. Valid entity types: 'Asset', 'Shot', ... 290 names ...` |
| `"shots"` (REST slug) | 400, same message |
| `"action_menu_items"` (REST slug), `"Shots"` (plural label) | 400, same message |
| `"ZzprobeNotAType"` | 400, same message |
| `"PermissionRuleSet.HumanUser"` (a value real rows hold) | 400, same message |
| `"CustomEntity19"` (enabled on this site) | 200, reads back `"CustomEntity19"` |
| `"CustomEntity08"` (not in `/schema`) | 200, reads back `"CustomEntity08"` |
| `"CustomEntity29_sg_scene_Connection"` | 200, reads back as sent |
| `{"type": "Shot", "id": 1}` | 400 `API update() ActionMenuItem.entity_type expected [String, NilClass] data type(s) but got ActionDispatch::Http::ParamsHashWithIndifferentAccess: {"type" => "Shot", "id" => 1}` |
| `["Shot", "Asset"]`, `0` | 400 `... expected [String, NilClass] data type(s) but got Array: ["Shot", "Asset"]` / `... but got Integer: 0` |
| key omitted on create | 201, reads back `null` |
| `"Asset"` on create | 201, reads back `"Asset"` |
| `"ZzprobeNotAType"` on create | 400 `Invalid field value, update failed [5 - Update failed for [ActionMenuItem.entity_type]: 'ZzprobeNotAType' is not a valid entity type. Valid entity types: ...]` + `crud_error_uuid` |

The error enumerates the legal set the way the operator error does, and it is the only place that set is
published: all 290 built-in names, including 75 `CustomEntityNN`, 60 `CustomNonProjectEntityNN`, 15
`CustomThreadedEntityNN` and 45 `*Connection` types, enabled or not. On the probed site every `/schema` name
is in it, and `CustomEntity08`, absent from `/schema`, still writes at 200.

A read-only one says so rather than failing silently:

```
PUT /entity/steps/<id>  {"entity_type": "Asset"}
 -> 400  "API update() Step.entity_type is editable on create only."
```

**Clear**

| sent | reads back | matched by `is None` | matched by `is ''` |
|---|---|---|---|
| `"Shot"` (control) | `"Shot"` | 0 | 0 |
| `null` | `null` | 1 | 1 |
| `""` | `null` | 1 | 1 |

`is ''` is an alias for `is None`. There is no "set but blank" state.

**Filter** Four operators, the same four a `list` has:

```
[["entity_type", "definitely_not_an_operator", null]] -> 400
 title:  "API read() Step.entity_type's 'entity_type' data type doesn't support
          'definitely_not_an_operator' 'relation'"
 source: {"Step.entity_type": " data type doesn't support 'definitely_not_an_operator' 'relation'.
          Value: {"path" => "entity_type", "relation" => "definitely_not_an_operator", "values" => [nil]}
          Valid relations: ["is", "is_not", "in", "not_in"]"}
```

Baseline 35 Steps site-wide.

| operator | value | matches |
|---|---|---|
| `is` | `"Shot"` | 12 |
| `is` | `"shot"` (wrong case) or `"shots"` (REST slug) | 0 |
| `is` | `"ZzprobeNotAType"`, or a real type with no rows | 0 |
| `is` | `null` or `""` | 0 |
| `is_not` | `"Shot"` | 23 |
| `is_not` | `null` | 35 |
| `in` | `["Shot", "Asset"]` | 25 |
| `in` | `["Shot", "ZzprobeNotAType"]` | 12; the junk member is dropped, no error |
| `in` | `"Shot"` (bare, not a list) | 12; a scalar is accepted where a list is expected |
| `in` | `["ZzprobeNotAType"]` | 0 |
| `not_in` | `["Shot"]` | 23 |
| `is` | `{"type": "Shot", "id": 1}` | 400 `expected [String, NilClass] data type(s) but got ActionDispatch::Http::ParamsHashWithIndifferentAccess` |
| `in` | `{"type": "Shot", "id": 1}` | 400, the same body |
| `contains` | any | 400, same "doesn't support ... 'relation'" body |
| `starts_with` | any | 400, the same body |
| `name_is` | any | 400, the same body |
| `type_is` | any | 400, the same body |

**Traps**
- Not an `entity` field. `entity` stores a `{type, id}` link under `relationships` and takes the entity
  vocabulary (`type_is`, `name_contains`, nine operators); `entity_type` stores the type name alone under
  `attributes` and takes four. An `{type, id}` hash 400s on both read and write here.
- Filters are case-sensitive, unlike a `list`, where `'type a'` matches `'Type A'`. `"shot"` returns 0 rows
  with no error, so a lowercased value reads as "nothing matches".
- The 290-name legal set is the built-in type table, not the site's schema. Validate against
  `/schema` before writing, or store a type name that has no endpoint.
- Existing rows hold values the validator rejects: `PermissionRuleSet.entity_type` reads
  `PermissionRuleSet.HumanUser`, and writing that back 400s. Never round-trip a read value into an update.
- Four of the five are read-only, and a write to one 400s with `is editable on create only.`
