---
tags: [schema, custom-field, write, list-field, status-list, entity-field, error-handling, trap]
endpoints: [PUT /schema/<Type>/fields/<field>, POST /schema/<Type>/fields/<field>, GET /schema/<Type>/fields/<field>]
phase: schema
scope: api
measured: site-wide, 2026-11-10; three retired fields on Version revived, written and retired; three reverse-field names spent
coverage: partial
unmeasured: whether the field the 500 retired can be revived, and the order valid_types take at creation. The first is the site owner's call, the second needs a new name.
verdict: A PUT applies all its properties or none, in any order. A description or name cannot be emptied. `valid_types` keeps the sent order, and a lowercase type name is a 500 that retires the field.
---

# 121_field_settings_edges

**Q** Can a field's description be cleared, can its lists be emptied, does one `PUT` take several
properties, is the order of an entity field's valid types kept, and what does a value the site does
not know answer?

**Endpoint** `PUT /schema/<Type>/fields/<field>`

**Docs claim** `/spec.json` types every property value as a string and documents no refusal.

**Actual**

```
PUT description "", or null; name "", or null; valid_values [], or null; valid_types [], or null
  -> 400 code 103 "title": "Request Parameters invalid."
     "source": {"properties": {"0": {"value": ["value must be filled"]}}}
PUT description " "  (name " " is the same with 'name') -> 400 code 103
  "title": "API schema_field_update() invalid/missing 'description' value string:\n
   {\"property_name\" => \"description\", \"value\" => \" \"}"
PUT description " zzprobe 121 pad " -> 200, reads back with both spaces

PUT list  [valid_values ["p","q"], default_value "q"] -> 200, both changed
PUT list  [default_value "r", valid_values ["r","s"]] -> 200, both changed
PUT list  [default_value "s", valid_values ["t","u"]] -> 400 code 103, neither changed
  "title": "API schema_field_update() 'default_value' not in valid_values :\n
   {\"property_name\" => \"default_value\", \"value\" => \"s\"}"
PUT list  [description "...", default_value "zzz"], either order -> the same 400, description unchanged
PUT status_list  [valid_values ["vwd","apr"], default_value "vwd"] from ["na","rev"], "na" -> 200
PUT status_list  [default_value "na", valid_values ["na","rev"]] -> 200, both changed

PUT entity  valid_types ["Asset","Shot"] over ["Shot","Asset"] -> 200, reads ["Asset","Shot"]
PUT entity  valid_types ["Sequence","Shot","Asset"] -> 200, reads ["Sequence","Shot","Asset"]

PUT status_list  valid_values [..., "zzq"], or default_value "zzq" -> 400 code 103
  "title": "API schema_field_update() invalid/missing 'status_list' string"
  "source": {"status": "invalid/missing 'status_list' string:\n\"zzq\"\nValid statuses:\n[\"act\", ...]"}
PUT entity  valid_types ["Shot","ZzNoSuchType"] -> 400 code 103
  "title": "API schema_field_update() invalid/missing entity"
  "source": {"entity_type": "invalid/missing entity:\n\"ZzNoSuchType\"\nValid types:\n[\"ActionMenuItem\", ...]"}
PUT entity  valid_types ["shot"] -> 500 code 100 "title": "Shotgun Server Error"
  GET the field -> 404 "Field 'Version.sg_zzprobe_116_entity' does not exist."   DELETE -> 404
```

**Emptying**

| sent | on | result |
|---|---|---|
| `description` `""` or `null` | `list` | 400 `value must be filled` |
| `description` `" "` or `"  "` | `list` | 400 `invalid/missing 'description' value string` |
| `description` with no `value` key | `list` | 400, `source` reads `value is missing` |
| `description` `" text "` | `list` | 200, stored with its spaces |
| `name` `""` or `null` | `list` | 400 `value must be filled` |
| `name` `" "` | `list` | 400 `invalid/missing 'name' value string` |
| `valid_values` `[]` or `null` | `list`, `status_list` | 400 `value must be filled` |
| `valid_types` `[]` or `null` | `entity` | 400 `value must be filled` |

Every refusal left the field unchanged. A field created without a description reads
`description.value` `""`, and no request sent returned a field to that state.

**Several properties in one `PUT`**

| properties, in the order sent | on | result |
|---|---|---|
| `valid_values`, then a `default_value` only the new values hold | `list`, `status_list` | 200, both applied |
| that `default_value`, then the `valid_values` | `list`, `status_list` | 200, both applied |
| `valid_values` without the current default, with a new default | `status_list` | 200. The `valid_values` alone is a 400 (probe 116) |
| a `default_value` only the old values hold, then new `valid_values` | `list` | 400 `'default_value' not in valid_values`, neither applied |
| `description` and a refused `default_value`, either order | `list` | 400, `description` unchanged |
| `description` and `unique` | `list` | 400 `invalid property 'unique'`, `description` unchanged |
| `name` and `description` | `list` | 200, both applied |
| `description` twice | `list` | 200, the second value |

The values are checked against the state the whole request would leave, not against the field as
it is and not in the order sent.

**Order and repeats**

| sent | on | reads back |
|---|---|---|
| `valid_types`, the same types in another order | `entity` | 200, the order sent. A reorder is a change |
| `valid_types`, three types | `entity` | the order sent, not alphabetical |
| `valid_types` `["Shot","Shot","Asset"]` | `entity` | `["Shot","Asset"]` |
| `valid_values` `["alpha","alpha","beta"]` | `list` | `["alpha","beta"]` |
| `valid_values` with a status code twice | `status_list` | **both kept**: `["na","vwd","apr","na"]` |

**A value the site does not have**

| sent | result |
|---|---|
| a status code that is no Status, in `valid_values` or as `default_value` | 400. `source.status` lists the valid codes. No Status was created |
| a name that is no entity type, in `valid_types` | 400. `source.entity_type` lists every entity type, connection types included |
| an entity type in the wrong case, `"shot"` | **500 code 100, and the field is gone**: `GET` and `DELETE` answer 404 |

On the probed site `source.status` held 41 codes and `GET /entity/statuses` returned 32 rows.

After the 500 the event log shows the field's retirement date set, its reverse fields retired and
`allowed_entity_types` stored as `["shot"]`, with no retirement event for the field itself. A revive
of it was not attempted.

**Reverse fields**

The event log shows an `entity` field on Version holding a field on each of its valid types, named
`sg_versions_<n>`, as a `multi_entity` does (probe 116).

| write | event log |
|---|---|
| a type added to `valid_types` | a new field created on that type |
| a type removed | that field retired |
| a removed type added back | a new field under the next number. The retired one is not revived |
| the entity field retired, or revived | its reverse fields retired, or revived, with it |
| any of those | the site preferences `view_master_settings` and `creative_review_settings` rewritten with the same value, and `use_<type>_sg_versions_<n>_connections` set |

A retired name stays taken (probe 019), so each removal and return of a type spends one name on
that type. This run spent three.

**Teaches**

| do | why |
|---|---|
| Never plan to empty a description, a display name or a list | every form is a 400, and whitespace alone is a 400 too |
| Send `valid_values` and `default_value` in one `PUT` | the pair is checked together, so a status list moves to new values and a new default in one request |
| Treat a `PUT` as all or nothing | one refused property left the others unapplied in every case sent |
| Compare `valid_types` as an ordered list | the order sent is the order read |
| Add and remove valid types only when the set changes | each added type creates a field on that type and each removed one spends its name |
| Check every `valid_types` name against `GET /schema`, case included, before sending | an unknown name is a 400, a wrong case is a 500 that takes the field down |
| Deduplicate a status list's `valid_values` yourself | a repeated code is stored twice |
