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
- **A delivery record is written whether or not anything answers.** A hook pointed at a dead host
  records `status: "delivered"` with `response_code: 0` and an empty `body`. **`delivered` means
  dispatched, not received.** Never read that status as confirmation a consumer got the payload; read
  `response_code`, which is 0 when nothing replied.
- **A hook's own status change is delivered to the hook.** Setting `status` to `disabled` and back
  writes one delivery record each. Its event type is not in the guide's list of 39 custom events:

  ```json
  {"data": {"id": "0", "event_type": "Webhook_Status_Change", "event_log_entry_id": 0,
            "webhook_status": "disabled", "previous_webhook_status": "active",
            "meta": {"type": "webhook_status_change", "source": "client",
                     "old_value": "active", "new_value": "disabled"}},
   "timestamp": "2026-09-04T18:47:18Z"}
  ```

  `id` is `"0"` and `event_log_entry_id` is `0`: this is generated by the webhook service itself and
  has no row in the event log behind it. A consumer must tolerate it, because no subscription asks
  for it and every toggled hook is sent one.
- **On the probed site, entity events reach no hook, and this is not a REST problem.** A hook created
  in the web interface and one created over REST behave identically: `active`, correctly subscribed,
  and no delivery record for any entity change or for `test_connection`, while `Webhook_Status_Change`
  on the same hook in the same minute records normally. Two public endpoints were tried, a tunnel
  proven reachable in-process and webhook.site. So the delivery recorder runs and the entity-event
  feed into it does not. Diagnose a silent hook by toggling its status: a record proves the pipeline
  is alive and isolates the fault to the event feed.
- Because no entity event was delivered, `X-SG-SIGNATURE`, the entity payload, the
  `x-sg-event-batch-*` headers, `batch_deliveries`, and `PUT /webhook/deliveries/<record_uuid>` and
  `redeliver` are all unprobed.
- Everything here uses `entity_types`. The second subscription mode the 400 names, `event_type`, the
  fourth lifecycle action `revive`, and the entity families the guide excludes are all measured in
  `050_webhook_subscriptions`.
