---
endpoint: PUT /entity/<type>/<id>
tags: [write, silent]
scope: api
measured: sandbox project written
verdict: Updates and returns the whole record, 77 attribute keys for a Shot. A key left out of the body is unchanged rather than cleared, and an empty body is a 200 no-op.
---

# PUT /entity/<type>/<id>

**Params**

| part | value |
|---|---|
| body | only the keys to change |
| `?fields` | accepted and ignored |

**Sample requests**

```python
ID = 7650
r = c.put(f"/entity/shots/{ID}", json={"description": "written by probe 041"})
print(r.status_code, len(r.json()["data"]["attributes"]))
# 200 77, the whole record, not the change
```

A second write that names only `code`:

```python
r = c.put(f"/entity/shots/{ID}", json={"code": "sh010_renamed"})
r.json()["data"]["attributes"]["description"]
# 'written by probe 041', untouched, not cleared
```

An id that is not there:

```json
{"errors": [{"status": 404, "code": 104, "title": "Not Found",
             "detail": "Entity of type [Shot] with id=999999999 does not exist."}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | updated, or nothing sent |
| 404 | `Entity of type [Shot] with id=999999999 does not exist.`, code 104 |

**Edge cases**

| you send | result |
|---|---|
| `{"description": "x"}` | set |
| a body omitting `description` | unchanged, not cleared |
| `{}` | 200, nothing happens |
| `null` for a clearable field | cleared |

- There is no PATCH. `PUT` here is already a partial update, which is the opposite of what the verb
  usually means: it does not replace the record with the body.
- Clearing is per data type, not universal. `""` on a text field stores `null`; `null` on a `color`
  field is refused outright; a bare list on a `multi_entity` replaces every link.

**Links**

- `field_types/multi_entity`
- `field_types/text`
- `recipes/009_multi_entity_safely`
- `findings/024_read_after_write`