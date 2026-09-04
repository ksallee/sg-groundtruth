---
endpoint: POST /webhook/hooks/<record_uuid>/test_connection
coverage: partial
unmeasured: Answers 204 for any uuid and produced no delivery record on the probed site. What it does on a working site is unmeasured.
tags: [webhook, silent, trap]
scope: api
measured: called against a real hook and a uuid that is not a hook
verdict: Answers 204 for any uuid, a hook that does not exist included, and confirms nothing about the hook, the endpoint or whether anything was sent.
---

# POST /webhook/hooks/<record_uuid>/test_connection

**Params**

| part | value |
|---|---|
| `<record_uuid>` | any uuid. It is not checked |
| body | none |

**Sample requests**

```python
r = c.post(f"/webhook/hooks/{uuid}/test_connection")   # 204, empty body
```

**Response codes**

| status | when |
|---|---|
| 204 | always, for a real hook and for a uuid that is not a hook alike |

**Edge cases**

- **204 is not a delivery.** The same 204 comes back for a uuid that names no hook, so the status code
  reports only that the request was accepted.
- On the probed site nothing reached a listener proven reachable from the public internet in the same
  run, and no delivery record was written, within 180s of a 204. Whatever this call schedules was not
  observable through either the endpoint or the API.
- Do not use it as a health check, and do not treat a 204 as evidence the hook works.

**Links**

- `endpoints/get_webhook_hooks_hook_id_deliveries`
- `findings/045_webhooks`
