---
endpoint: POST /webhook/deliveries/<record_uuid>/redeliver
tags: [webhook, delivery, error-handling]
scope: api
measured: called only against a uuid that is not a delivery
verdict: A uuid that is not a delivery answers 404 code 104 with `detail` `delivery: <uuid> not found`. No delivery was observed on the probed site, so the call itself is unprobed.
---

# POST /webhook/deliveries/<record_uuid>/redeliver

**Params**

| part | value |
|---|---|
| `<record_uuid>` | the `id` of a delivery record, from `GET /webhook/hooks/<hook_id>/deliveries` |

**Sample requests**

Unprobed. This call sends one delivery again, and no delivery record existed on the probed site to make it against.

```python
r = c.post(f"/webhook/deliveries/{delivery_uuid}")
```

**Response codes**

| status | when |
|---|---|
| 404 code 104 | a well-formed uuid that is not a delivery. `detail` is `delivery: <uuid> not found` |

**Edge cases**

- **Unprobed against a real delivery.** The 404 above is the only measured behaviour. Probe 045
  produced no delivery to act on: see `findings/045_webhooks`.

**Links**

- `endpoints/get_webhook_hooks_hook_id_deliveries`
- `findings/045_webhooks`
