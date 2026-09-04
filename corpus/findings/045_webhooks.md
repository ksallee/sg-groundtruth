---
tags: [webhook, silent, trap, create, write, delivery, error-handling, token]
endpoints: [GET /webhook/hooks, POST /webhook/hooks, GET /webhook/hooks/<record_uuid>, PUT /webhook/hooks/<record_uuid>, DELETE /webhook/hooks/<record_uuid>, POST /webhook/hooks/<record_uuid>/test_connection, GET /webhook/hooks/<hook_id>/deliveries, GET /webhook/deliveries/<record_uuid>, PUT /webhook/deliveries/<record_uuid>, POST /webhook/deliveries/<record_uuid>/redeliver]
phase: write
scope: api
measured: sandbox project written, one Shot created and updated, hooks created and deleted in-run
verdict: The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.
---

# 045_webhooks

**Q** How does a client subscribe to events over REST, and what does the create contract check?

**Endpoint** `POST /webhook/hooks ; GET|PUT|DELETE /webhook/hooks/<uuid> ; POST /webhook/hooks/<uuid>/test_connection`

**Docs claim** The public Webhooks guide documents the web interface and never mentions this REST
family: it directs a reader to the Webhooks Page or an Event Log to create one. It states
`X-SG-SIGNATURE` as `sha1=<hmac-sha1(token, body)>`, a 1MB payload cap that strips `old_value` and
`new_value` and adds a `warning` key, a 6-second response timeout, 4KB acknowledgements, delivery
records kept seven days, a lifecycle of `active`/`unstable`/`failed`/`disabled` with 100 failures in
24 hours reaching `failed`, one minute of response time per minute per site, and delivery from
the `us-east-1` region. It recommends webhook.site for testing. None of that is verified here.

**Actual**

```
POST /webhook/hooks, which url passes the validator
  https://localhost:9/... http://127.0.0.1:9/... https://10.255.255.1/...
  https://192.0.2.1/...   https://<name>.invalid/hook  https://<name>.example.com/hook  zzprobe_045
    -> 400 {"url": ["url should be a valid url, not a shotgun site or reserved/internal ip address"]}
  ftp://example.com/zzprobe-045                                        -> 201   scheme unchecked

POST /webhook/hooks, the create contract
  {}                                              -> 400 {"url": ["url is missing"],
       "entity_types": ["entity_types either entity types or event type is required"]}
  {"entity_types": {"Shot": {"zzprobe_045": []}}} -> 400 {"entity_types": ["entity_types is not valid"]}
  {"entity_types": {"ZzProbe045": {"create": []}}}-> 400 {"entity_types": ["entity_types is not valid"]}
  {"entity_types": {"Shot": {"update": ["zzprobe_045_nope"]}}}         -> 201   field never checked
  {"entity_types": {"Shot": {"create": []}, "Asset": {"create": []}}}  -> 201   two types accepted
  {"projects": [999999999]}                                            -> 201   project never checked
  Content-Type: application/vnd+shotgun.api3_array+json -> 415
       {"content_type": "Content-Type must be one of: 'application/json'."}

PUT /webhook/hooks/<uuid>
  {}                       -> 400 {"ensure_field_present": ["at least one field must be provided"]}
  {"status": "zzprobe_045"}-> 400 {"status": ["status must be one of: active, disabled"]}
  {"description": "..."}   -> 200, every other key kept

POST /webhook/hooks/<uuid>/test_connection            -> 204
POST /webhook/hooks/<a uuid that is not a hook>/test_connection -> 204
GET  /webhook/hooks/<a uuid that is not a hook>       -> 404 code 104 "hook: <uuid> not found"
GET  /webhook/hooks/not_a_uuid                        -> 404 code 103 detail null
DELETE -> 204, then GET 404, deliveries 404, DELETE again 404
```

**Teaches**

| sent | result |
|---|---|
| a field the type does not have, in `update` | 201, and the hook can never fire |
| two entity types in one hook | 201 |
| a project id that is not there | 201 |
| an action name the API does not have | 400 `entity_types is not valid` |
| an entity type the site does not have | 400 `entity_types is not valid` |

- **The url validator resolves the host and ignores the scheme.** Every unroutable target is refused
  with one message naming reserved and internal addresses, `https://<name>.example.com` included,
  while `ftp://example.com/...` answers 201. Passing validation means the host resolved, not that the
  hook can be delivered to.
- **`test_connection` answers 204 for a uuid that is not a hook.** It confirms nothing: not that the
  hook exists, not that the endpoint is reachable, not that anything was sent. Do not use it as a
  health check.
- `POST /webhook/hooks` refuses the vendor array content type that `_search` requires, at 415 naming
  `application/json`. The webhook family takes plain JSON only (`004_array_vs_hash`).
- The two 404 shapes are the parser, not the lookup: a well-formed uuid that names nothing answers code
  104 with `detail` naming it, and a segment that is not a uuid answers code 103 with `detail` null.
- **No hook created over REST has been observed to deliver.** Two independent public endpoints were
  tried, a tunnel proven reachable from outside in the same process and webhook.site, which the guide
  itself recommends. Both: 0 requests, 0 delivery records, `num_deliveries` 0, hook still `active`,
  across 180s and 150s. `generate_event_log_entries` was on and probe 049 confirms the events existed.
  On the probed site 61 of 63 active hooks also show `num_deliveries: 0`, and the one hook that has
  ever delivered reports 29. Whether a hook created in the web interface behaves differently is the
  open question; until it is answered do not read this as evidence the API never delivers.
- Because nothing was delivered, `X-SG-SIGNATURE`, the payload, the `x-sg-event-batch-*` headers,
  `batch_deliveries`, and `GET|PUT /webhook/deliveries/<record_uuid>` and `redeliver` are all unprobed.
- Everything here uses `entity_types`. The second subscription mode the 400 names, `event_type`, the
  fourth lifecycle action `revive`, and the entity families the guide excludes are all measured in
  `050_webhook_subscriptions`.
