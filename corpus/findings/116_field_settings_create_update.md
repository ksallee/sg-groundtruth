---
tags: [schema, custom-field, create, write, list-field, status-list, entity-field, multi-entity, error-handling, trap]
endpoints: [POST /schema/<Type>/fields, PUT /schema/<Type>/fields/<field>, GET /schema/<Type>/fields/<field>]
phase: schema
scope: api
measured: site-wide, 2026-11-10; six fields created on Version, updated and retired
coverage: partial
unmeasured: a status code the site does not have, in valid_values. Not sent, because what the server does with it is unknown. Blocked on the work.
verdict: A create takes description, unique, valid_values, default_value and valid_types. `unique` and a multi_entity's valid_types never change afterwards; an entity's valid_types and list values do.
---

# 116_field_settings_create_update

**Q** Which settings does a custom field take at creation, where does each read back, and which can
be changed afterwards?

**Endpoint** `POST /schema/<Type>/fields ; PUT /schema/<Type>/fields/<field>`

**Docs claim** `/spec.json` types every property value as a string and lists no property names.

**Actual**

```
POST list  name, description, valid_values ["alpha","beta","gamma"], default_value "beta" -> 201
POST text  name, description, unique true -> 201     unique reads {"value": true, "editable": false}
POST checkbox  name, default_value true -> 201
POST status_list  name alone -> 400 code 103
  "API schema_field_create() missing required 'properties' [\"valid_values\"]"
POST status_list  name, valid_values ["na","rev","vwd"], default_value "rev" -> 201
POST entity  name, valid_types ["Shot","Asset"] -> 201   valid_types {"value": ["Shot","Asset"], "editable": true}
POST multi_entity  name, valid_types ["Shot","Asset"] -> 400 code 103
  "API schema_field_create() 'valid_types' value expected Array with one element: ..."
POST multi_entity  name, valid_types ["Shot"] -> 201     valid_types {"value": ["Shot"], "editable": false}

PUT list  default_value "zzz" -> 400 "API schema_field_update() 'default_value' not in valid_values : ..."
PUT list  valid_values ["beta"] while default_value is "alpha" -> 200, default_value still "alpha"
PUT status_list  valid_values ["rev"] while default_value is "na" -> 400
  "API schema_field_update() 'valid_values' [\"rev\"] must include the 'default_value' 'na'"
PUT any  default_value null, or "" -> 400 "Request Parameters invalid."
  source {"properties": {"0": {"value": ["value must be filled"]}}}
PUT list  unique true -> 400 "API schema_field_update() invalid property 'unique': ... Valid property
  names: [\"name\", \"visible\", \"description\", \"summary_default\", \"valid_values\",
  \"default_value\", \"custom_metadata\"]"
PUT text (created unique)  unique false -> 500 code 105
  "API schema_field_update() does not support updating 'unique'."
PUT list  {"unique": true, "properties": [description]} -> 200, description changed, unique unchanged
PUT multi_entity  valid_types, any value, the one it holds included -> 400
  "API schema_field_update() can't update 'valid_types' on this field: ..."
PUT checkbox  default_value "false" -> 200, reads back the string "false"
```

**Where each setting reads back**, in `GET /schema/<Type>/fields/<field>` under `data`

| setting | path | sent at creation as |
|---|---|---|
| data type | `data_type.value` | top-level `data_type` |
| display name | `name.value` | property `name` |
| description | `description.value` | property `description` |
| unique | `unique.value` | property `unique` |
| default value | `properties.default_value.value` | property `default_value` |
| valid values | `properties.valid_values.value` | property `valid_values` |
| valid types | `properties.valid_types.value` | property `valid_types` |

A `status_list` also has `properties.display_values` and `properties.hidden_values`.

**At creation**

| type | sent | result |
|---|---|---|
| `list` | `valid_values`, `default_value`, `description` | 201, all three read back |
| `text` | `unique: true`, `description` | 201, `unique.value` true |
| `checkbox` | `default_value: true` | 201 |
| `status_list` | name alone | 400, `valid_values` required |
| `status_list` | `valid_values`, `default_value` | 201, both read back |
| `entity` | two `valid_types` | 201 |
| `multi_entity` | two `valid_types` | 400, exactly one |
| `multi_entity` | one | 201. The event log shows a second field retired with it, `version_sg_zzprobe_116_multi_entity_versions`, the reverse side of the link (probe 056) |

**After creation**, every request a `PUT` with `{"properties": [{"property_name": ..., "value": ...}]}`

| setting | on | result |
|---|---|---|
| `name` | any | applied. The programmatic name and the path do not change |
| `description`, `custom_metadata`, `summary_default` | any | applied |
| `valid_values`, added or removed | `list`, `status_list` | applied |
| `valid_values` without the current default | `list` | applied, and the default stays, outside the list |
| `valid_values` without the current default | `status_list` | refused, 400 `must include the 'default_value'` |
| `valid_values` as `[]` or a string | `list` | refused, 400 |
| `default_value`, a valid value | `list`, `status_list`, `checkbox` | applied |
| `default_value`, not a valid value | `list`, `status_list` | refused, 400 |
| `default_value` `null` or `""` | `list`, `status_list`, `checkbox` | refused, 400 `value must be filled`. No request sent cleared a default |
| `default_value` | `currency` (probe 117) | refused, 400 `default value is read-only for all data types except status_list, list, checkbox` |
| `default_value` as the string `"false"` | `checkbox` | **applied as the string**: 200 and it reads back `"false"`, not `false` |
| `valid_types`, added, removed or replaced | `entity` | applied |
| `valid_types`, any value | `multi_entity` | refused, 400 `can't update 'valid_types' on this field` |
| `unique` as a property | `list`, `currency` | refused, 400 `invalid property 'unique'` |
| `unique` as a property | `text` created unique | refused, 500 `does not support updating 'unique'` |
| `unique` at the top level beside `properties` | `list` | **ignored**: 200, unchanged |
| `properties: []` | any | refused, 400 `can't create/update with no 'properties'` |

**Teaches**

| do | why |
|---|---|
| Send every setting in the create | all of them are accepted there, and `unique` and a multi_entity's `valid_types` are accepted nowhere else |
| Read `<setting>.editable` before planning an update | `unique` reads false on every field and `valid_types` reads false on a multi_entity: both are the refused ones |
| Give a `status_list` its `valid_values` | a bare create is a 400 |
| Send booleans as booleans | a checkbox default of `"false"` is stored as a string |
| Remove a list's default before removing its value | a list keeps a default that is no longer a valid value |
| Do not plan to clear a default | `null` and `""` are both refused |

Probe 019 recorded "two types refused" without the link type. It was `multi_entity`: an `entity` field
takes several.
