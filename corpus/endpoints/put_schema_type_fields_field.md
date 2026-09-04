---
endpoint: PUT /schema/<Type>/fields/<field>
tags: [schema, custom-field, silent]
scope: api
measured: sandbox project written, probe 040
verdict: Changes a field's properties. A body changing `data_type` is a 200 that does nothing, so read the field back rather than trusting the status code.
---

# PUT /schema/<Type>/fields/<field>

**Params**

| part | value |
|---|---|
| `properties` | a list of `{property_name, value}`, the same shape the create takes |

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
| 200 | accepted, which is not the same as applied |

**Edge cases**

- `data_type` is immutable and the API does not say so. The write answers 200 and the value is
  unchanged. This is the sharpest case of the general rule that a 200 from this API proves the request
  parsed, not that it happened.
- Renaming changes the display name only. The programmatic name is fixed at creation, and a rename does
  not free the old one for reuse.

**Links**

- `endpoints/post_schema_type_fields`
- `findings/040_field_revive`
- `findings/028_loud_and_silent`