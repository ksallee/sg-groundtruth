---
endpoint: PUT /webhook/deliveries/<record_uuid>
coverage: partial
unmeasured: The acknowledgement never persisted on the probed site, where the webhook subsystem is degraded. Whether that is the API or the site is unresolved.
tags: [webhook, delivery, silent, trap]
scope: api
measured: site-wide, one delivery manufactured by toggling a hook's status
verdict: Answers 200 for an empty body, for a key it does not take, and for a valid acknowledgement that then reads back null. Only the 4096-byte cap is enforced.
---

# PUT /webhook/deliveries/<record_uuid>

**Params**

| part | value |
|---|---|
| `<record_uuid>` | a delivery `id` |
| `acknowledgement` | a string, 4096 bytes or less |

**Sample requests**

```python
r = c.put(f"/webhook/deliveries/{delivery_uuid}", json={"acknowledgement": "ack"})
```

```json
{ "errors": [ { "status": 400, "code": 103, "title": "Request Parameters invalid.",
    "source": { "acknowledgement": ["acknowledgement must be 4096 bytes long or less"] } } ] }
```

**Response codes**

| sent | status |
|---|---|
| `{"acknowledgement": "ack"}` | 200 |
| `{}` | 200 |
| `{"status": "failed"}`, a key the call does not take | 200 |
| `{"acknowledgement": <4096 bytes>}` | 200 |
| `{"acknowledgement": <4097 bytes>}` | 400 `acknowledgement must be 4096 bytes long or less` |

**Edge cases**

- **On the probed site the acknowledgement never persisted.** 200 every time, and a read back gives
  `null` after a short string and `""` after 4096 bytes. The one input that changes the answer is a
  body over the cap. That site's webhook subsystem is degraded (`045_webhooks`), so whether this is
  the API or the site is unresolved.
- An empty body answers 200 here, where `PUT /webhook/hooks/<record_uuid>` answers 400
  `ensure_field_present`. The two `PUT`s in this family do not share a contract.
- The cap is counted in **bytes**, not characters, and the error says so.

**Links**

- `endpoints/get_webhook_deliveries_record_uuid`
- `endpoints/put_webhook_hooks_record_uuid`
- `findings/045_webhooks`
