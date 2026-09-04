---
endpoint: GET /entity/<type>/<id>
coverage: measured
tags: [query, entity-field]
scope: api
measured: sample project 1 of 1
verdict: One row, and the only read where `fields` is honoured on a single record. A retired row is 404 here and 200 under `options[return_only]=retired`.
---

# GET /entity/<type>/<id>

**Params**

| part | value |
|---|---|
| `fields` | comma list, dotted paths allowed |
| `options[return_only]` | `retired` to read a deleted row |

**Sample requests**

```python
ID = 17055
r = c.get(f"/entity/versions/{ID}", params={"fields": "code,entity"})
```

```json
{
  "data": {
    "type": "Version",
    "attributes": { "code": "<version code>" },
    "relationships": {
      "entity": { "data": { "id": 1230, "name": "<asset name>", "type": "Asset" } }
    },
    "id": 17055,
    "links": { "self": "/api/v1/entity/versions/17055" }
  }
}
```

A row that was deleted:

```python
c.get("/entity/shots/7653").status_code                                        # 404
c.get("/entity/shots/7653", params={"options[return_only]": "retired"}).status_code   # 200
```

**Response codes**

| status | when |
|---|---|
| 200 | the row is live, or retired and asked for as retired |
| 404 | `Version: 999999999 not found`, code 104 |
| 404 | a retired row asked for normally, with the identical message |

**Edge cases**

- The 404 for "never existed" and the 404 for "retired" are the same message with the same code. Only a
  second call with `options[return_only]=retired` tells them apart, and that distinction is the whole of
  what `DELETE` does.
- Code 104 here, against code 103 for a bad type name. 104 is "this row is not there", 103 is "your
  request is wrong".
- This is the only read where `fields` is honoured on a single record. Every write ignores it.

**Links**

- `endpoints/delete_entity_type_id`
- `endpoints/get_entity_type`
- `findings/024_read_after_write`