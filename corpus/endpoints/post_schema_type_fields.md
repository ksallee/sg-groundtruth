---
endpoint: POST /schema/<Type>/fields
coverage: measured
tags: [schema, custom-field, create, silent, destructive]
scope: api
measured: site-wide, fields created on Version and retired, probes 019, 116 and 117
verdict: You send a display name and the server derives the `sg_` name, which is only in `links.self`. A duplicate display name is 201 with a silent `_1` suffix, so read `/fields` first.
---

# POST /schema/<Type>/fields

**Params**

| part | value |
|---|---|
| `data_type` | the type. `text float number date date_time list url duration percent footage currency timecode` take nothing else |
| `properties` | a list of `{property_name, value}`. `name` is the display name |
| `valid_types` | a property, required for `entity` and `multi_entity`. One or more for `entity`, exactly one for `multi_entity` (probe 116) |
| `valid_values` | a property, required for `status_list`, optional for `list` |
| `default_value` | a property, required for `checkbox`, optional for `list` and `status_list` |
| `description`, `unique` | optional properties. `unique` is accepted here and nowhere else |

**Sample requests**

```python
r = c.post("/schema/Version/fields",
           json={"data_type": "text",
                 "properties": [{"property_name": "name", "value": "zzprobe 019 With (Parens)"}]})
```

The programmatic name is **not** in the body. It is the last segment of `links.self`:

```json
{
  "data":  { "name": { "value": "zzprobe 019 With (Parens)" }, "data_type": { "value": "text" } },
  "links": { "self": "/api/v1/schema/Version/fields/sg_zzprobe_019_with__parens_" }
}
```

An entity field, where `properties` is not optional:

```python
r = c.post("/schema/Version/fields",
           json={"data_type": "entity",
                 "properties": [{"property_name": "name", "value": "Source Plate"},
                                {"property_name": "valid_types", "value": ["Shot"]}]})
```

`multi_entity` with `["Shot", "Asset"]`:

```json
{"errors": [{"status": 400, "code": 103,
             "title": "API schema_field_create() 'valid_types' value expected Array with one element: ..."}]}
```

That error is what two or more types answers on a `multi_entity`, where one element is 201. An
`entity` field takes several: `["Shot", "Asset"]` is 201 (probe 116).

**Response codes**

| status | when |
|---|---|
| 201 | created |
| 400 | `{"data_type": ["data_type is not valid"]}` for `color` and `image` |
| 400 | `'valid_types' value expected Array with one element` for two or more on a `multi_entity` |
| 400 | `missing required 'properties' ["valid_values"]` for a bare `status_list` |
| 400 | code 105, `schema_field_create() failed, there is a retired field with the same field_name: <name>`, with `source.field_name` |
| 500 | bare `checkbox`, `Only true or false allowed in checkbox` |
| 500 | `calculated`, `NoMethodError` |

**Edge cases**

Display name to programmatic name, measured:

| display name sent | name created |
|---|---|
| `zzprobe 019 With (Parens)` | `sg_zzprobe_019_with__parens_` |
| `sg_zzprobe_019_already_prefixed` | `sg_sg_zzprobe_019_already_prefixed`, prefixed twice |
| a name already in use | `<name>_1`, at 201, with no warning |
| `zzprobe 117 a--b..c!!d  e_f` | `sg_zzprobe_117_a__b__c__d__e_f`: one `_` per character, runs kept |
| `  zzprobe 117 spaces  ` | `sg___zzprobe_117_spaces__`, not trimmed |
| 120 ASCII characters | 123, uncut |
| any name holding a non-ASCII character, on `currency` | `sg_currency`: the display name is discarded (probe 117) |

- **Deleting a field does not free its name.** `DELETE` retires the field and the name stays taken,
  released only by emptying the Trash page in the web interface. An `ensure()` reads `/fields` first
  rather than posting and hoping, and a field created to test with is named `sg_zzprobe_<nnn>_*` so
  whoever empties that page can tell litter from a real field.
- `number` takes 2147483647 and 400s on 2\*\*63, so a 64-bit id or seed does not fit one.

**Links**

- `endpoints/delete_schema_type_fields_field`
- `endpoints/post_schema_type_fields_field`
- `findings/019_create_fields`
- `findings/040_field_revive`
- `findings/116_field_settings_create_update`
- `findings/117_field_types_and_names`