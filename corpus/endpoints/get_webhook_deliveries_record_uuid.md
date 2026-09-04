---
endpoint: GET /webhook/deliveries/<record_uuid>
coverage: partial
unmeasured: Measured against a Webhook_Status_Change delivery to a dead host. request_headers, response_headers, body and a non-zero response_code are unmeasured.
tags: [webhook, delivery, error-handling]
scope: api
measured: site-wide, one delivery manufactured by toggling a hook's status
verdict: Returns one delivery record with ten keys. `status` is `delivered` even when nothing answered, so read `response_code`, which is 0 when no response was received.
---

# GET /webhook/deliveries/<record_uuid>

**Params**

| part | value |
|---|---|
| `<record_uuid>` | a delivery `id`, from `GET /webhook/hooks/<hook_id>/deliveries` |

**Sample requests**

```python
r = c.get(f"/webhook/deliveries/{delivery_uuid}")
```

The record has ten keys. No entity-event delivery has been observed on the probed site, so the shape
below is the envelope only, from a `Webhook_Status_Change` delivery to a host that does not exist.
**`request_body` is not shown, because a status-change payload is not what an entity event sends**:
that payload is unrecorded, and the guide's example is the only description of it.

```json
{ "data": { "id": "<uuid>",
    "event_time": 1788548570,
    "status": "delivered",
    "process_time": 0,
    "body": "",
    "response_code": 0,
    "acknowledgement": null,
    "request_headers": null,
    "response_headers": null,
    "request_body": { "...": "the payload as sent" } },
  "links": { "self": "/api/v1/webhook/deliveries/<record_uuid>" } }
```

**Response codes**

| status | when |
|---|---|
| 200 | found |
| 404 code 104 | a well-formed uuid that is not a delivery. `detail` is `delivery: <uuid> not found` |

**Edge cases**

- **`status: "delivered"` means dispatched, not received.** This record answers `delivered` with
  `response_code: 0` and an empty `body`, and its target host does not exist. Read `response_code`.
- `request_body` holds the payload as sent, so a delivery can be inspected after the fact without
  instrumenting the consumer. What an entity event puts there is unrecorded here.
- `request_headers` and `response_headers` were both null here. Whether they populate when a consumer
  answers is unmeasured.

**Links**

- `endpoints/get_webhook_hooks_hook_id_deliveries`
- `endpoints/put_webhook_deliveries_record_uuid`
- `findings/045_webhooks`
