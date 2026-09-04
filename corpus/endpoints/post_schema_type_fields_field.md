---
endpoint: POST /schema/<Type>/fields/<field>
coverage: measured
tags: [schema, custom-field, discovery]
scope: api
measured: sandbox project written, probe 040
verdict: Revive a retired field, at 204. It is the only way to get a burnt name back, and it returns at its original `data_type` whatever the site wants now.
---

# POST /schema/<Type>/fields/<field>

A field name is taken forever once created. Recreating it is
`400 schema_field_create() failed, there is a retired field with the same field_name`. This is the way
back.

**Params**

| part | value |
|---|---|
| `<field>` | the retired programmatic name |
| `revive` | `true`. The only key, and it is required |

**Sample requests**

```python
r = c.post("/schema/Version/fields/sg_zzprobe_040_revive", json={"revive": True})
```

204, no body. Read the field back to see what came back:

```python
c.get("/schema/Version/fields/sg_zzprobe_040_revive").json()["data"]["data_type"]["value"]
# 'text', the type it was created at, whatever the site wants now
```

An empty body, which is how the parameter was found:

```python
r = c.post("/schema/Version/fields/sg_zzprobe_040_revive", json={})
```

```json
{"errors": [{"status": 400, "code": 103, "source": {"revive": ["revive is missing"]}}]}
```

**Response codes**

| status | when |
|---|---|
| 204 | revived, empty body |
| 400 | `source: {"revive": ["revive is missing"]}` on a body without it |

**Edge cases**

- The revived field keeps its **original** `data_type`. A name burnt as `text` cannot come back as
  `number`, and the `PUT` that would change it is a 200 that does nothing.
- The API named this parameter itself, in the 400 for an empty body. Nothing in the documentation does.

**Links**

- `endpoints/put_schema_type_fields_field`
- `endpoints/delete_schema_type_fields_field`
- `findings/040_field_revive`