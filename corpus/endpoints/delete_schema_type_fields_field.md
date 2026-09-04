---
endpoint: DELETE /schema/<Type>/fields/<field>
tags: [schema, custom-field, destructive]
scope: api
measured: sandbox project written, probe 019
verdict: Retires a field at 204 and burns its programmatic name forever: the same name will not create again, only revive. Treat this as irreversible from REST.
---

# DELETE /schema/<Type>/fields/<field>

**Params**

| part | value |
|---|---|
| `<field>` | the programmatic name |

**Sample requests**

```python
r = c.delete("/schema/Version/fields/sg_my_field")
print(r.status_code, repr(r.text))
# 204 ''
```

What changed, in order:

```python
c.get("/schema/Version/fields/sg_my_field").status_code       # 404
"sg_my_field" in c.get("/schema/Version/fields").json()["data"]   # False
```

Creating the same display name again:

```json
{"errors": [{"status": 400, "code": 103,
  "title": "API schema_field_create() failed, there is a retired field with the same field_name: sg_my_field. Delete the retired field forever from the Trash Page in Shotgun and try again."}]}
```

**Response codes**

| status | when |
|---|---|
| 204 | retired, empty body |

**Edge cases**

- **The name is not freed.** The error tells you to empty the Trash page in the web interface, which
  REST cannot do. From an API client the only way back is
  `POST /schema/<Type>/fields/<field>` with `{"revive": true}`, and it returns at the original type.
- The collision is on the programmatic name alone. Recreating at a different `data_type` is the
  identical 400.
- A probe cannot clean up after itself here the way it can for a row. Test on a stock field, and where
  one has to be created, name it `sg_zzprobe_<nnn>_*` so it is identifiable when the Trash page is
  emptied.

**Links**

- `endpoints/post_schema_type_fields_field`
- `findings/019_create_fields`
- `findings/040_field_revive`