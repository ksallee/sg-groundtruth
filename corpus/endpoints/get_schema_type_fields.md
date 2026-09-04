---
endpoint: GET /schema/<Type>/fields
coverage: measured
tags: [schema, cost, fill-rate, discovery]
scope: api
measured: sample project 1 of 1
verdict: Every field on one type with its `data_type`, `editable` and `mandatory`. The expensive call at 48KB and ~330ms, so fetch the types you need and never loop the `/schema` listing into it.
---

# GET /schema/<Type>/fields

**Params**

| part | value |
|---|---|
| `project_id` | optional. Adds `hidden_values` to every list and status field (probe 009) |

**Sample requests**

```python
r = c.get("/schema/Version/fields")
```

Keyed by programmatic field name. On the probed site, Version has 71 fields in 47958 bytes:

```json
{
  "data": {
    "code": {
      "name":        { "value": "Version Name", "editable": true },
      "entity_type": { "value": "Version",      "editable": false },
      "data_type":   { "value": "text",         "editable": false },
      "editable":    { "value": true,           "editable": false },
      "mandatory":   { "value": true,           "editable": false },
      "unique":      { "value": false,          "editable": false },
      "properties":  { "default_value": { "value": null, "editable": false } }
    }
  }
}
```

Which fields a client may write:

```python
f = c.get("/schema/Version/fields").json()["data"]
print([k for k, v in f.items() if v["editable"]["value"]])
```

**Response codes**

| status | when |
|---|---|
| 200 | the type is enabled |
| 404 | `Entity type 'X' does not exist.` |

**Edge cases**

- `mandatory` is not the create contract. `code` reads `mandatory: true` and a create omitting it
  succeeds at 201 with a server-invented name; `project` reads `mandatory: false` and a create omitting
  it is 400. Read the create contract from the entity-type card, not from this flag.
- Every value is wrapped in `{value, editable}`, and the outer `editable` says whether you may change
  the property, not whether you may write the field. `data["code"]["editable"]["value"]` is the one that
  answers "can I write this".
- Adding `project_id` changes the body by 28 bytes on the probed site: only `hidden_values` appears.
  Everything else is identical at every scope.
- 48KB and about 330ms per type. Never loop this over the `/schema` listing.

**Links**

- `endpoints/get_schema_type_fields_field`
- `findings/002_schema`
- `findings/012_create_version`
- `findings/007_fill_rates`