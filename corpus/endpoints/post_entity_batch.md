---
endpoint: POST /entity/_batch
coverage: measured
tags: [write, batch, create, silent]
scope: api
measured: sandbox project written
verdict: The key is `requests`, not `data`, and sending `data` is 400 `requests is missing`. It answers 200 rather than 201, and one bad request rolls the whole batch back.
---

# POST /entity/_batch

**Params**

| part | value |
|---|---|
| `requests` | the list. **Not** `data`, which is what the response uses |
| each entry | `{"request_type": "create"\|"update"\|"delete", "entity": "Shot", ...}` |
| create | `data` with the attributes |
| update | `record_id` and `data` |
| delete | `record_id` |

**Sample requests**

```python
r = c.post("/entity/_batch", json={"requests": [
    {"request_type": "create", "entity": "Shot",
     "data": {"project": {"type": "Project", "id": 1180}, "code": "sh010"}},
    {"request_type": "update", "entity": "Shot", "record_id": 7652,
     "data": {"description": "batched"}}]})
```

One envelope per request, each wrapping its own `data`. The nesting is one level deeper than a
single-row create:

```json
{
  "data": [
    { "data": { "type": "Shot",
                "attributes": { "code": "sh010", "sg_status_list": "wtg" },
                "id": 7654 } },
    { "data": { "type": "Shot", "attributes": { "description": "batched" }, "id": 7652 } }
  ]
}
```

Sending the list under `data`, which is the key the response uses:

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
             "source": {"requests": ["requests is missing"]}}]}
```

One bad request in an otherwise good batch:

```python
r = c.post("/entity/_batch", json={"requests": [
    {"request_type": "create", "entity": "Shot",
     "data": {"project": {"type": "Project", "id": 1180}, "code": "sh011"}},
    {"request_type": "update", "entity": "Shot", "record_id": 999999999, "data": {"description": "x"}}]})
print(r.status_code)   # 404
# and afterwards, searching for sh011 returns 0 rows
```

**Response codes**

| status | when |
|---|---|
| 200 | applied. Not 201, even for a batch that is all creates |
| 400 | `Request Parameters invalid.`, `source: {"requests": ["requests is missing"]}` |
| 404 | any request naming a row that is not there, and nothing in the batch is applied |

**Edge cases**

- **It is atomic.** The Shot the first request would have created does not exist after the 404.
- The response nesting is the trap that outlives a run. Reading `row["id"]` instead of
  `row["data"]["id"]` yields `None`, so cleanup silently skips the rows and they stay on the site.
- A returned id does not by itself prove the row exists. Read back after a batch that matters.
- The request key and the response key differ by name. `requests` in, `data` out.

**Links**

- `endpoints/post_entity_type`
- `recipes/002_batch`
- `recipes/005_propagate_status`
- `findings/028_loud_and_silent`