# Endpoints — Webhooks

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `GET /webhook/deliveries/<record_uuid>` **[partial]**

Returns one delivery record with ten keys. `status` is `delivered` even when nothing answered, so read `response_code`, which is 0 when no response was received.

not measured: Measured against a Webhook_Status_Change delivery to a dead host. request_headers, response_headers, body and a non-zero response_code are unmeasured.

- **`status: "delivered"` means dispatched, not received.** This record answers `delivered` with
  `response_code: 0` and an empty `body`, and its target host does not exist. Read `response_code`.

- `request_body` holds the payload as sent, so a delivery can be inspected after the fact without
  instrumenting the consumer. What an entity event puts there is unrecorded here.

- `request_headers` and `response_headers` were both null here. Whether they populate when a consumer
  answers is unmeasured.

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`

**Silent on this call**

- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.

`corpus/endpoints/get_webhook_deliveries_record_uuid.md`

## `PUT /webhook/deliveries/<record_uuid>` **[partial]**

Answers 200 for an empty body, for a key it does not take, and for a valid acknowledgement that then reads back null. Only the 4096-byte cap is enforced.

not measured: The acknowledgement never persisted on the probed site, where the webhook subsystem is degraded. Whether that is the API or the site is unresolved.

- **On the probed site the acknowledgement never persisted.** 200 every time, and a read back gives
  `null` after a short string and `""` after 4096 bytes. The one input that changes the answer is a
  body over the cap. That site's webhook subsystem is degraded (`045_webhooks`), so whether this is
  the API or the site is unresolved.

- An empty body answers 200 here, where `PUT /webhook/hooks/<record_uuid>` answers 400
  `ensure_field_present`. The two `PUT`s in this family do not share a contract.

- The cap is counted in **bytes**, not characters, and the error says so.

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`

**Silent on this call**

- `put_webhook_deliveries_record_uuid` — Answers 200 for an empty body, for a key it does not take, and for a valid acknowledgement that then reads back null. Only the 4096-byte cap is enforced.
- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.

`corpus/endpoints/put_webhook_deliveries_record_uuid.md`

## `POST /webhook/deliveries/<record_uuid>/redeliver` **[partial]**

Answers 204 with no body. On the probed site no second delivery record followed, so 204 reports that the request was accepted and nothing more.

not measured: Answers 204 and produced no second delivery on the probed site. Whether it redelivers anywhere is unmeasured.

- On the probed site the hook's delivery count was unchanged ten seconds after a 204, and no second
  record appeared. That site does not deliver entity events at all (`045_webhooks`), so this is not
  evidence the call does nothing everywhere.

- 204 has no delivery id in it, so a caller cannot correlate a redelivery with its result. Poll
  `GET /webhook/hooks/<hook_id>/deliveries` and compare.

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`

**Silent on this call**

- `post_webhook_deliveries_record_uuid_redeliver` — Answers 204 with no body. On the probed site no second delivery record followed, so 204 reports that the request was accepted and nothing more.
- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.

`corpus/endpoints/post_webhook_deliveries_record_uuid_redeliver.md`

## `GET /webhook/hooks`

Lists every hook on the site, not only this script's. `status` takes active or disabled and a value no hook has answers 200 with zero rows rather than 400.

- The listing is site-wide. A hook another integration registered is returned with its third-party url
  and its `entity_types`, so a script reading this sees every subscription on the site.

- `is_token_set` is a boolean. The token itself is never returned.

- `links.next` is present on an empty page, as everywhere else in this API (`006_pagination`).

- A `status` the enum does not have answers 200 with zero rows. There is no error to distinguish a
  filter typo from a site with no matching hooks.

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`
- `011_audit_webhook_subscriptions` (recipes) — Inventory every webhook subscription on a site, and see which have ever delivered  
  rules: `doors/recipes`

**Silent on this call**

- `get_webhook_hooks` — Lists every hook on the site, not only this script's. `status` takes active or disabled and a value no hook has answers 200 with zero rows rather than 400.
- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.
- `011_audit_webhook_subscriptions` — Inventory every webhook subscription on a site, and see which have ever delivered

`corpus/endpoints/get_webhook_hooks.md`

## `POST /webhook/hooks`

`url` and `entity_types` are required and the entity type and action are checked. A field name, a project id and a second entity type are all accepted without being checked.

- The url validator resolves the host and does not check the scheme. `https://<name>.example.com/hook`
  is refused with `url should be a valid url, not a shotgun site or reserved/internal ip address`,
  while `ftp://example.com/...` answers 201.

- Omitting `projects` subscribes the hook to the whole site. There is no confirmation step.

- A field name in `update` that the type does not have answers 201. The hook is created and can never
  fire on it.

- Two entity types in one hook answer 201.

- A `projects` id that does not exist answers 201 and is stored.

- `entity_types` and `event_type` are mutually exclusive and share one error message, so
  `entity_types either entity types or event type is required` also means "you sent both".

- An entity type the guide excludes from webhooks, `ApiUser` and `EventLogEntry` among them, is
  accepted at 201 (`050_webhook_subscriptions`).

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`
- `050_webhook_subscriptions` (findings) — entity_types and event_type are mutually exclusive and one 400 covers giving neither and giving both. revive is a fourth action, and every entity the guide calls excluded is accepted at 201.  
  rules: `doors/findings-write`

**Silent on this call**

- `post_webhook_hooks` — `url` and `entity_types` are required and the entity type and action are checked. A field name, a project id and a second entity type are all accepted without being checked.
- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.
- `050_webhook_subscriptions` — entity_types and event_type are mutually exclusive and one 400 covers giving neither and giving both. revive is a fourth action, and every entity the guide calls excluded is accepted at 201.

`corpus/endpoints/post_webhook_hooks.md`

## `GET /webhook/hooks/<hook_id>/deliveries` **[partial]**

Takes status, entity_type, entity_id, from and acknowledgement as query params and answers 200 with zero rows for any of them. No delivery was observed, so the record shape is unprobed.

not measured: Only Webhook_Status_Change deliveries were observed. The record for an entity event, and every field that only an answering consumer fills, are unmeasured.

- The body has `included` and `performance_metrics` alongside `data`. `performance_metrics` reports
  zeros rather than being absent when there is nothing to measure.

- **The record shape is unprobed.** No delivery was observed on the probed site, so the keys of a
  delivery, its response code and its timing fields are unknown here.

- **`num_deliveries` and this listing disagree in both directions, and what the counter counts is
  unmeasured.** On the probed site one hook reports `num_deliveries: 29` and returns zero records,
  and a hook that returns two records reports `num_deliveries: 0`. The guide says records are kept
  seven days, which explains the first case and not the second. Neither field alone answers "has this
  hook ever delivered"; read both.

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`
- `011_audit_webhook_subscriptions` (recipes) — Inventory every webhook subscription on a site, and see which have ever delivered  
  rules: `doors/recipes`

**Silent on this call**

- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.
- `011_audit_webhook_subscriptions` — Inventory every webhook subscription on a site, and see which have ever delivered

`corpus/endpoints/get_webhook_hooks_hook_id_deliveries.md`

## `GET /webhook/hooks/<record_uuid>`

Returns the hook without its token. A well-formed uuid naming nothing answers 404 code 104, a segment that is not a uuid answers 404 code 103 with `detail` null.

- `entity_types` is returned with its action keys reordered. Compare it as a mapping, not as text.

- The token is never returned. `is_token_set` is the only readable fact about it.

- `num_deliveries` does not track the deliveries listing. On the probed site one hook reports 29 with
  zero records, and a hook with two records reports 0. What the counter counts is unmeasured; it does
  not count `Webhook_Status_Change` deliveries.

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`
- `050_webhook_subscriptions` (findings) — entity_types and event_type are mutually exclusive and one 400 covers giving neither and giving both. revive is a fourth action, and every entity the guide calls excluded is accepted at 201.  
  rules: `doors/findings-write`
- `011_audit_webhook_subscriptions` (recipes) — Inventory every webhook subscription on a site, and see which have ever delivered  
  rules: `doors/recipes`

**Silent on this call**

- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.
- `050_webhook_subscriptions` — entity_types and event_type are mutually exclusive and one 400 covers giving neither and giving both. revive is a fourth action, and every entity the guide calls excluded is accepted at 201.
- `011_audit_webhook_subscriptions` — Inventory every webhook subscription on a site, and see which have ever delivered

`corpus/endpoints/get_webhook_hooks_record_uuid.md`

## `PUT /webhook/hooks/<record_uuid>`

A partial body edits only the keys it names. An empty body is 400, and `status` takes active or disabled and names both in the error.

- A key omitted from the body is left alone. This is a partial update, not a replace.

- The error enumerates the legal statuses, so the vocabulary is readable from a deliberate 400 without
  reading the documentation.

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`

**Silent on this call**

- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.

`corpus/endpoints/put_webhook_hooks_record_uuid.md`

## `DELETE /webhook/hooks/<record_uuid>`

204 and the hook is gone at once: the hook, its deliveries listing and a second delete all answer 404 immediately after.

- The delete is immediate and total. `GET` on the hook, `GET` on its deliveries and a second `DELETE`
  all answer 404 in the same run, so a hook's delivery history goes with it.

- There is no retire-and-revive here as there is for entities (`040_field_revive`). Deleting is the
  only way to stop a hook other than setting `status` to `disabled`, which keeps it readable.

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`
- `050_webhook_subscriptions` (findings) — entity_types and event_type are mutually exclusive and one 400 covers giving neither and giving both. revive is a fourth action, and every entity the guide calls excluded is accepted at 201.  
  rules: `doors/findings-write`

**Silent on this call**

- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.
- `050_webhook_subscriptions` — entity_types and event_type are mutually exclusive and one 400 covers giving neither and giving both. revive is a fourth action, and every entity the guide calls excluded is accepted at 201.

`corpus/endpoints/delete_webhook_hooks_record_uuid.md`

## `POST /webhook/hooks/<record_uuid>/test_connection` **[partial]**

Answers 204 for any uuid, a hook that does not exist included, and confirms nothing about the hook, the endpoint or whether anything was sent.

not measured: Answers 204 for any uuid and produced no delivery record on the probed site. What it does on a working site is unmeasured.

- **204 is not a delivery.** The same 204 comes back for a uuid that names no hook, so the status code
  reports only that the request was accepted.

- On the probed site nothing reached a listener proven reachable from the public internet in the same
  run, and no delivery record was written, within 180s of a 204. Whatever this call schedules was not
  observable through either the endpoint or the API.

- Do not use it as a health check, and do not treat a 204 as evidence the hook works.

**Measured by**

- `045_webhooks` (findings) — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  rules: `doors/findings-write`

**Silent on this call**

- `post_webhook_hooks_record_uuid_test_connection` — Answers 204 for any uuid, a hook that does not exist included, and confirms nothing about the hook, the endpoint or whether anything was sent.
- `045_webhooks` — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.

`corpus/endpoints/post_webhook_hooks_record_uuid_test_connection.md`
