---
endpoint: POST /entity/<type>/<id>
coverage: measured
tags: [write, trap]
scope: api
measured: sandbox project written
verdict: Revives a retired row. `?revive=1` is required and any JSON body is discarded, so this is not an update via POST.
---

# POST /entity/<type>/<id>

The inverse of `DELETE /entity/<type>/<id>`. It is not a create and not an update.

**Params**

| part | value |
|---|---|
| `?revive` | required, and must be truthy: `1`, `true`, `yes` |
| body | accepted and discarded |
| `?fields` | accepted and ignored |

**Sample requests**

A row retired by `DELETE`:

```python
ID = 7683
c.delete(f"/entity/shots/{ID}").status_code          # 204
r = c.post(f"/entity/shots/{ID}", params={"revive": 1})
```

```json
{"data": {"type": "Shot", "id": 7683},
 "links": {"self": "/api/v1/entity/shots/7683"},
 "meta": {"did_revive": true}}
```

The same call on a row that was never retired:

```json
{"data": {"type": "Shot", "id": 7683},
 "links": {"self": "/api/v1/entity/shots/7683"},
 "meta": {"did_revive": false}}
```

Reaching for it as a `PUT`:

```python
c.post(f"/entity/shots/{ID}", json={"description": "written by POST"})
```

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
             "source": {"revive": ["revive is missing"]}}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | revived, or already live. `meta.did_revive` says which |
| 400 | `source: {"revive": ["revive is missing"]}` |
| 400 | `source: {"revive": ["revive must be true"]}` for `0` or `false` |
| 404 | `Entity of type [Version] with id=999999999 does not exist.`, code 104 |

**Edge cases**

| you send | result |
|---|---|
| `?revive=1`, `?revive=true`, `?revive=yes` | revived |
| `?revive=0`, `?revive=false` | 400 `revive must be true` |
| no `revive` parameter | 400 `revive is missing` |
| a body of field values | 200, the fields are not applied |
| `?fields=code` | 200, no `attributes` returned either way |

- The response has no `attributes` key at all, which is thinner than any other write returns. Re-read
  the id to see the record.
- Field values survive the retire and come back with the revive. Nothing is reset.
- `did_revive: false` at 200 is the only signal that the row was already live. Read `meta`, not the
  status code.

**Links**

- `endpoints/delete_entity_type_id`
- `endpoints/put_entity_type_id`
- `endpoints/get_entity_type_id`
- `findings/024_read_after_write`
