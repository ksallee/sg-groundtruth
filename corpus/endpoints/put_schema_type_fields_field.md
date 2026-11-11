---
endpoint: PUT /schema/<Type>/fields/<field>
coverage: measured
tags: [schema, custom-field, silent]
scope: api
measured: sandbox project written, probes 040, 115, 116 and 119
verdict: Changes a field's properties. A body changing `data_type` is a 200 that does nothing, so read the field back rather than trusting the status code.
---

# PUT /schema/<Type>/fields/<field>

**Params**

| part | value |
|---|---|
| `properties` | a list of `{property_name, value}`, the same shape the create takes. Required and not empty |
| `project_id` | in the JSON body or the query. Required when `visible` is among the properties, and scopes only `visible` (probe 115) |

**Sample requests**

A rename, which works:

```python
r = c.put("/schema/Version/fields/sg_my_field",
          json={"properties": [{"property_name": "name", "value": "Renamed"}]})
```

A type change, which does not:

```python
r = c.put("/schema/Version/fields/sg_zzprobe_040_revive", json={"data_type": "number"})
print(r.status_code)
# 200
c.get("/schema/Version/fields/sg_zzprobe_040_revive").json()["data"]["data_type"]["value"]
# 'text', unchanged
```

**Response codes**

| status | when |
|---|---|
| 200 | accepted, which is not the same as applied. The body is the whole field |
| 400 | code 104 `The 'visible' property requires a project to be updated.` |
| 400 | code 105 `The Project with the given project_id does not exist.` |
| 400 | `invalid property '<name>'`, followed by the valid property names for that field |
| 400 | `Request Parameters invalid.` with `value must be filled` for a `null`, `""` or `[]` value |
| 404 | `Field '<Type>.<field>' does not exist.`, for a retired field and an unused name alike (probe 119) |
| 500 | code 105 `does not support updating 'unique'.` on a `text` field |

**Edge cases**

- `data_type` is immutable and the API does not say so. The write answers 200 and the value is
  unchanged. This is the sharpest case of the general rule that a 200 from this API proves the request
  parsed, not that it happened.
- A property the update does not take is a 400 that lists the ones it does. For `hidden_values` on a
  status field the list was `name`, `visible`, `description`, `summary_default`, `default_value`,
  `valid_values`, `custom_metadata`, with or without `project_id` (probe 114). `hidden_values` cannot
  be written over REST.
- A top-level key the call does not take is ignored when `properties` is present: `{"unique": true,
  "properties": [...]}` is a 200 that applies the properties and leaves `unique` alone (probe 116).
- Which properties a field takes depends on its `data_type`, and the field says so: each one reads
  `editable: true` in `GET /schema/<Type>/fields/<field>`. Probe 116 has the table.
- Renaming changes the display name only. The programmatic name is fixed at creation, and a rename does
  not free the old one for reuse.

**Links**

- `endpoints/post_schema_type_fields`
- `findings/040_field_revive`
- `findings/028_loud_and_silent`
- `findings/115_field_visibility_per_project`
- `findings/116_field_settings_create_update`