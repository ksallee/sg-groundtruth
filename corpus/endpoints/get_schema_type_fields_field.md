---
endpoint: GET /schema/<Type>/fields/<field>
coverage: measured
tags: [schema, status, list-field]
scope: api
measured: sample project 1 of 1
verdict: One field's properties, at 1211 bytes against 48KB for the whole type. Pass `project_id` or `hidden_values` is empty and your status picker offers statuses the project refuses.
---

# GET /schema/<Type>/fields/<field>

**Params**

| part | value |
|---|---|
| `<field>` | the programmatic name, `sg_status_list`. Not the display name |
| `project_id` | optional, and the only thing that varies by project |

**Sample requests**

Site scope:

```python
r = c.get("/schema/Version/fields/sg_status_list")
```

```json
{
  "data": {
    "name":       { "value": "Status",       "editable": true },
    "data_type":  { "value": "status_list",  "editable": false },
    "editable":   { "value": true,           "editable": false },
    "mandatory":  { "value": false,          "editable": false },
    "properties": { "default_value": { "value": "rev", "editable": true } }
  }
}
```

Project scope, which is the only call that answers "which statuses may I use here":

```python
PROJECT = 70
p = c.get("/schema/Version/fields/sg_status_list",
          params={"project_id": PROJECT}).json()["data"]["properties"]
print([v for v in p["valid_values"]["value"] if v not in p["hidden_values"]["value"]])
```

On the probed site and project: 16 `valid_values`, `hidden_values` `['pndl', 'pndvs']`, so 14 usable.

**Response codes**

| status | when |
|---|---|
| 200 | the field exists on that type |
| 404 | `Field 'Version.sg_not_a_field' does not exist.` |

**Edge cases**

- Without `project_id`, `hidden_values` is empty and the same 16 come back. A picker built on the
  site-scope answer offers statuses the project's own interface refuses.
- REST does not enforce the subtraction on write. A hidden status writes and reads back fine, so every
  client subtracts `hidden_values` itself.
- The 404 names the type and the field together, `Version.sg_not_a_field`, which is the only error on
  the schema endpoints that says which half you got wrong.

**Links**

- `field_types/status_list`
- `findings/009_status_lists`
- `recipes/010_status_picker`