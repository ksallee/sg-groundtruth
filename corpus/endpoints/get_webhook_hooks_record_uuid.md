---
endpoint: GET /webhook/hooks/<record_uuid>
tags: [webhook, error-handling]
scope: api
measured: one hook created and read back in-run
verdict: Returns the hook without its token. A well-formed uuid naming nothing answers 404 code 104, a segment that is not a uuid answers 404 code 103 with `detail` null.
---

# GET /webhook/hooks/<record_uuid>

**Params**

| part | value |
|---|---|
| `<record_uuid>` | the `id` returned by `POST /webhook/hooks` |

**Sample requests**

```python
r = c.get(f"/webhook/hooks/{uuid}")
```

```json
{ "data": { "id": "<uuid>", "url": "https://<host>/hook",
    "entity_types": { "Shot": { "create": [], "delete": [],
                                "update": ["sg_status_list", "description"] } },
    "status": "active", "projects": [1180], "num_deliveries": 0,
    "is_token_set": true, "name": "status watcher" },
  "links": { "self": "/api/v1/webhook/hooks/<uuid>" } }
```

**Response codes**

| status | when |
|---|---|
| 200 | found |
| 404 code 104 | a well-formed uuid that is not a hook. `detail` is `hook: <uuid> not found` |
| 404 code 103 | a segment that is not a uuid. `detail` is null |

**Edge cases**

- `entity_types` is returned with its action keys reordered. Compare it as a mapping, not as text.
- The token is never returned. `is_token_set` is the only readable fact about it.
- `num_deliveries` does not track the deliveries listing. On the probed site one hook reports 29 with
  zero records, and a hook with two records reports 0. What the counter counts is unmeasured; it does
  not count `Webhook_Status_Change` deliveries.

**Links**

- `endpoints/get_webhook_hooks_hook_id_deliveries`
- `findings/045_webhooks`
