---
endpoint: POST /webhook/hooks
tags: [webhook, create, silent, trap, token]
scope: api
measured: hooks created and deleted in-run against the sandbox project
verdict: `url` and `entity_types` are required and the entity type and action are checked. A field name, a project id and a second entity type are all accepted without being checked.
---

# POST /webhook/hooks

**Params**

| part | value |
|---|---|
| `Content-Type` | `application/json` only. The vendor array type answers 415 |
| `url` | required. The host must resolve and must not be internal |
| `entity_types` | required. `{"<Type>": {"create"\|"update"\|"delete": [<field>, ...]}}` |
| `projects` | optional. Omitted means the whole site |
| `token` | optional. Signs the delivery. Never returned; `is_token_set` reports it |
| `name`, `description`, `validate_ssl_cert`, `batch_deliveries` | optional |

**Sample requests**

```python
r = c.post("/webhook/hooks", json={
    "url": "https://<host>/hook",
    "entity_types": {"Shot": {"create": [], "update": ["sg_status_list"]}},
    "projects": [1180], "name": "status watcher", "token": "<secret>"})
```

```json
{ "data": { "id": "<uuid>", "url": "https://<host>/hook",
    "entity_types": { "Shot": { "create": [], "update": ["sg_status_list"] } },
    "status": "active", "projects": [1180], "num_deliveries": 0,
    "validate_ssl_cert": true, "batch_deliveries": false, "is_token_set": true },
  "links": { "self": "/api/v1/webhook/hooks/<uuid>" } }
```

**Response codes**

| status | when |
|---|---|
| 201 | created, `status` `active` |
| 400 | `url` or `entity_types` missing, url unroutable, entity type or action unknown |
| 415 | `Content-Type: application/vnd+shotgun.api3_array+json` |

**Edge cases**

- The url validator resolves the host and does not check the scheme. `https://<name>.example.com/hook`
  is refused with `url should be a valid url, not a shotgun site or reserved/internal ip address`,
  while `ftp://example.com/...` answers 201.
- Omitting `projects` subscribes the hook to the whole site. There is no confirmation step.
- A field name in `update` that the type does not have answers 201. The hook is created and can never
  fire on it.
- Two entity types in one hook answer 201.
- A `projects` id that does not exist answers 201 and is stored.

**Links**

- `endpoints/get_webhook_hooks`
- `endpoints/post_webhook_hooks_record_uuid_test_connection`
- `findings/045_webhooks`
- `findings/004_array_vs_hash`
