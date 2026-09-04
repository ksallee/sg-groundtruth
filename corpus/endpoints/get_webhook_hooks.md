---
endpoint: GET /webhook/hooks
coverage: measured
tags: [webhook, paging, silent]
scope: api
measured: site-wide, one listing
verdict: Lists every hook on the site, not only this script's. `status` takes active or disabled and a value no hook has answers 200 with zero rows rather than 400.
---

# GET /webhook/hooks

**Params**

| part | value |
|---|---|
| `status` | `active` or `disabled`. Optional |
| `page[size]`, `page[number]` | default size 500 |

**Sample requests**

```python
r = c.get("/webhook/hooks", params={"status": "active"})
```

```json
{ "data": [ { "id": "<uuid>", "url": "https://<host>/hook",
    "entity_types": { "Version": { "update": ["sg_status_list"] } },
    "status": "active", "projects": [], "num_deliveries": 0,
    "validate_ssl_cert": true, "batch_deliveries": true,
    "is_token_set": true, "name": "", "description": "" } ],
  "links": { "self": "/api/v1/webhook/hooks",
             "next": "/api/v1/webhook/hooks?page%5Bnumber%5D=2&page%5Bsize%5D=500" } }
```

**Response codes**

| status | when |
|---|---|
| 200 | including for a `status` value no hook has, where `data` is `[]` |

**Edge cases**

- The listing is site-wide. A hook another integration registered is returned with its third-party url
  and its `entity_types`, so a script reading this sees every subscription on the site.
- `is_token_set` is a boolean. The token itself is never returned.
- `links.next` is present on an empty page, as everywhere else in this API (`006_pagination`).
- A `status` the enum does not have answers 200 with zero rows. There is no error to distinguish a
  filter typo from a site with no matching hooks.

**Links**

- `endpoints/post_webhook_hooks`
- `findings/045_webhooks`
- `findings/006_pagination`
