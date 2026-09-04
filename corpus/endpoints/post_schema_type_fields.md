---
endpoint: POST /schema/<Type>/fields
tags: [schema, custom-field, create, silent, destructive]
scope: api
measured: sandbox project written, probe 019
verdict: You send a display name and the server derives the `sg_` name, which is only in `links.self`. A duplicate display name is 201 with a silent `_1` suffix, so read `/fields` first.
---

# POST /schema/<Type>/fields

**Params**

| part | value |
|---|---|
| `data_type` | the type. `text float number date date_time list url duration percent footage` take nothing else |
| `properties` | a list of `{property_name, value}`. `name` is the display name |
| `valid_types` | required for `entity` and `multi_entity`, and exactly one element |
| `default_value` | required for `checkbox` |

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

```json
{"errors": [{"status": 400, "code": 103,
             "title": "'valid_types' value expected Array with one element"}]}
```

That error is what two or more types answers. One element is 201.

**Response codes**

| status | when |
|---|---|
| 201 | created |
| 400 | `{"data_type": ["data_type is not valid"]}` for `color` and `image` |
| 400 | `'valid_types' value expected Array with one element` for two or more |
| 400 | `schema_field_create() failed, there is a retired field with the same field_name` |
| 500 | bare `checkbox`, `Only true or false allowed in checkbox` |
| 500 | `calculated`, `NoMethodError` |

**Edge cases**

Display name to programmatic name, measured:

| display name sent | name created |
|---|---|
| `zzprobe 019 With (Parens)` | `sg_zzprobe_019_with__parens_` |
| `sg_zzprobe_019_already_prefixed` | `sg_sg_zzprobe_019_already_prefixed`, prefixed twice |
| a name already in use | `<name>_1`, at 201, with no warning |

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