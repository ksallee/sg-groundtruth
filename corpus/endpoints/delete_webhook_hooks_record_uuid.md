---
endpoint: DELETE /webhook/hooks/<record_uuid>
tags: [webhook, destructive]
scope: api
measured: hooks created and deleted in-run
verdict: 204 and the hook is gone at once: the hook, its deliveries listing and a second delete all answer 404 immediately after.
---

# DELETE /webhook/hooks/<record_uuid>

**Params**

| part | value |
|---|---|
| `<record_uuid>` | the hook `id` |

**Sample requests**

```python
r = c.delete(f"/webhook/hooks/{uuid}")   # 204, empty body
```

**Response codes**

| status | when |
|---|---|
| 204 | deleted, no body |
| 404 | already deleted, or never a hook |

**Edge cases**

- The delete is immediate and total. `GET` on the hook, `GET` on its deliveries and a second `DELETE`
  all answer 404 in the same run, so a hook's delivery history goes with it.
- There is no retire-and-revive here as there is for entities (`040_field_revive`). Deleting is the
  only way to stop a hook other than setting `status` to `disabled`, which keeps it readable.

**Links**

- `endpoints/put_webhook_hooks_record_uuid`
- `findings/045_webhooks`
