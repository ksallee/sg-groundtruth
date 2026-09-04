---
endpoint: PUT /webhook/hooks/<record_uuid>
tags: [webhook, write, status]
scope: api
measured: one hook created and edited in-run
verdict: A partial body edits only the keys it names. An empty body is 400, and `status` takes active or disabled and names both in the error.
---

# PUT /webhook/hooks/<record_uuid>

**Params**

| part | value |
|---|---|
| `Content-Type` | `application/json` |
| body | at least one of `url`, `entity_types`, `projects`, `token`, `name`, `description`, `status`, `validate_ssl_cert`, `batch_deliveries` |

**Sample requests**

```python
r = c.put(f"/webhook/hooks/{uuid}", json={"description": "status watcher, v2"})
```

```json
{ "data": { "id": "<uuid>", "description": "status watcher, v2",
    "entity_types": { "Shot": { "create": [], "delete": [],
                                "update": ["sg_status_list", "description"] } },
    "status": "active", "num_deliveries": 0, "is_token_set": true } }
```

**Response codes**

| status | when |
|---|---|
| 200 | updated, whole hook returned |
| 400 | empty body: `{"ensure_field_present": ["at least one field must be provided"]}` |
| 400 | `{"status": ["status must be one of: active, disabled"]}` |

**Edge cases**

- A key omitted from the body is left alone. This is a partial update, not a replace.
- The error enumerates the legal statuses, so the vocabulary is readable from a deliberate 400 without
  reading the documentation.

**Links**

- `endpoints/post_webhook_hooks`
- `findings/045_webhooks`
