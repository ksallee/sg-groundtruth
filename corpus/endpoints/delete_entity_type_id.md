---
endpoint: DELETE /entity/<type>/<id>
tags: [write, destructive]
scope: api
measured: sandbox project written
verdict: Retires a row at 204 with an empty body. It is not erased: the row reads 404 normally and 200 under `options[return_only]=retired`, and a second delete is 404.
---

# DELETE /entity/<type>/<id>

**Params**

| part | value |
|---|---|
| body | none |

**Sample requests**

```python
r = c.delete("/entity/shots/7653")
print(r.status_code, repr(r.text))
# 204 ''
```

The body is empty, so parsing it as JSON raises after the delete has already happened.

What the row does afterwards:

```python
c.get("/entity/shots/7653").status_code                                       # 404
c.get("/entity/shots/7653", params={"options[return_only]": "retired"}).status_code  # 200, 4525 bytes
c.delete("/entity/shots/7653").status_code                                    # 404
```

**Response codes**

| status | when |
|---|---|
| 204 | retired. Empty body, zero bytes |
| 404 | already retired, or never existed: `Entity of type [Shot] with id=7653 does not exist.` |

**Edge cases**

- Retired, not erased. Anything counting rows has to decide which of those two it means, and the default
  for every read is live-only.
- The correct spelling is `options[return_only]=retired`. `options[retired_only]=true` is accepted at
  200 and silently ignored, which reads as "there are no retired rows".
- A second delete is 404, so delete is not idempotent in its status code even though it is in its effect.

**Links**

- `endpoints/get_entity_type_id`
- `endpoints/post_entity_batch`
- `findings/025_event_log`