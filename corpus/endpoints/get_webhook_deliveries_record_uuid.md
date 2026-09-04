---
endpoint: GET /webhook/deliveries/<record_uuid>
coverage: partial
unmeasured: Measured against a Webhook_Status_Change delivery to a dead host. request_headers, response_headers, body and a non-zero response_code are unmeasured.
tags: [webhook, delivery, error-handling]
scope: api
measured: site-wide, one delivery manufactured by toggling a hook's status
verdict: Returns the whole delivery including `request_body`, the payload as sent. `status` is `delivered` even when nothing answered, so read `response_code`, which is 0 when nothing answered.
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

```json
{ "data": {
    "id": "570d1ac0-37c1-47e0-ab79-2dd780e573a8",
    "event_time": 1788548570,
    "status": "delivered",
    "process_time": 0,
    "body": "",
    "response_code": 0,
    "acknowledgement": null,
    "request_headers": null,
    "response_headers": null,
    "request_body": {
      "data": { "id": "0", "event_type": "Webhook_Status_Change",
                "event_log_entry_id": 0, "webhook_status": "disabled",
                "previous_webhook_status": "active",
                "meta": { "type": "webhook_status_change", "source": "client",
                          "old_value": "active", "new_value": "disabled" } },
      "timestamp": "2026-09-04T19:02:50Z" } },
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
- `request_body` is the payload as sent, so this call is how a delivery is inspected after the fact
  without instrumenting the consumer.
- `request_headers` and `response_headers` were both null here. Whether they populate when a consumer
  answers is unmeasured.

**Links**

- `endpoints/get_webhook_hooks_hook_id_deliveries`
- `endpoints/put_webhook_deliveries_record_uuid`
- `findings/045_webhooks`
