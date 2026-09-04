---
intent: Inventory every webhook subscription on a site, and see which have ever delivered
tags: [webhook, read-only, permission, silent]
endpoints: [GET /webhook/hooks, GET /webhook/hooks/<record_uuid>, GET /webhook/hooks/<hook_id>/deliveries]
scope: api
measured: site-wide, one listing of 63 hooks on the probed site
---

# 011_audit_webhook_subscriptions

## Call

```python
# get is FPT.get from src/sg_groundtruth/client.py; it adds auth and the /api/v1 prefix.
# The listing is site-wide: it returns every hook, not the ones this script created.
hooks = get("/webhook/hooks").json()["data"]

for h in hooks:
    # num_deliveries is the lifetime counter. The deliveries listing keeps seven days, so a hook
    # that last fired eight days ago returns an empty list and a non-zero count. Probe 045.
    ever = h["num_deliveries"]
    recent = get(f"/webhook/hooks/{h['id']}/deliveries").json()["data"]
    print(f"{h['status']:9s} {ever:>6} ever  {len(recent):>4} in 7d  "
          f"{sorted(h['entity_types'] or {}) or h.get('event_type')}  {h['url']}")
```

## Response

```json
{ "data": [ { "id": "<uuid>",
      "url": "https://<third-party host>/hook",
      "entity_types": { "Version": { "update": ["sg_status_list"] } },
      "status": "active", "projects": [], "num_deliveries": 0,
      "validate_ssl_cert": true, "batch_deliveries": true,
      "is_token_set": true, "name": "", "description": "" } ],
  "links": { "self": "/api/v1/webhook/hooks",
             "next": "/api/v1/webhook/hooks?page%5Bnumber%5D=2&page%5Bsize%5D=500" } }
```

On the probed site this returned 63 hooks, of which 61 were `active` with `num_deliveries: 0`, one
`disabled` with 29, and one `disabled` with 0.

## Notes

- **The listing is the whole site.** A script with API access reads every other integration's consumer
  url, its `entity_types` and its project scoping. Treat the output as sensitive.
- The secret token is never returned. `is_token_set` is the only readable fact about it.
- `num_deliveries: 0` on an `active` hook means it has never delivered in its lifetime, not that it is
  idle. That is the one field that separates a working subscription from a subscription that was
  accepted and never fired, which the create contract cannot tell you (`045_webhooks`).
- A hook may name `entity_types` or `event_type`, never both, so read whichever is populated
  (`050_webhook_subscriptions`).
- `status` is one of `active`, `unstable`, `failed` or `disabled`. Only `disabled` is set by a caller;
  the other three are the site's own assessment of the endpoint's health.
