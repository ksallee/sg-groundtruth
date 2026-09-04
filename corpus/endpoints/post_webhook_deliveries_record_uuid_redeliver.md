---
endpoint: POST /webhook/deliveries/<record_uuid>/redeliver
coverage: partial
unmeasured: Answers 204 and produced no second delivery on the probed site. Whether it redelivers anywhere is unmeasured.
tags: [webhook, delivery, silent]
scope: api
measured: site-wide, one delivery manufactured by toggling a hook's status
verdict: Answers 204 with no body. On the probed site no second delivery record followed, so 204 reports that the request was accepted and nothing more.
---

# POST /webhook/deliveries/<record_uuid>/redeliver

**Params**

| part | value |
|---|---|
| `<record_uuid>` | a delivery `id` |
| body | none |

**Sample requests**

```python
r = c.post(f"/webhook/deliveries/{delivery_uuid}/redeliver")   # 204, empty body
```

**Response codes**

| status | when |
|---|---|
| 204 | accepted |
| 404 code 104 | a well-formed uuid that is not a delivery |

**Edge cases**

- On the probed site the hook's delivery count was unchanged ten seconds after a 204, and no second
  record appeared. That site does not deliver entity events at all (`045_webhooks`), so this is not
  evidence the call does nothing everywhere.
- 204 has no delivery id in it, so a caller cannot correlate a redelivery with its result. Poll
  `GET /webhook/hooks/<hook_id>/deliveries` and compare.

**Links**

- `endpoints/get_webhook_hooks_hook_id_deliveries`
- `findings/045_webhooks`
