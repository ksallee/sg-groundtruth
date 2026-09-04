---
tags: [webhook, silent, trap, create, error-handling, enumeration]
endpoints: [POST /webhook/hooks, GET /webhook/hooks/<record_uuid>, DELETE /webhook/hooks/<record_uuid>]
phase: write
scope: api
measured: site-wide, 36 hooks created and deleted in the same statement; site hook count unchanged
verdict: entity_types and event_type are mutually exclusive and one 400 covers giving neither and giving both. revive is a fourth action, and every entity the guide calls excluded is accepted at 201.
---

# 050_webhook_subscriptions

**Q** What can a webhook subscribe to?

**Endpoint** `POST /webhook/hooks`

**Docs claim** The guide names two subscription groups, entity lifecycle events with the actions
*Created, Updated, Deleted and Revived*, and 39 custom events. It states webhooks are **not** available
for ApiUser, EventLogEntry or connection entities.

**Actual**

```
the second mode
  {"event_type": "Shotgun_User_Login"}          -> 201
  {"event_type": "Shotgun_User_Login", "projects": [<id>]} -> 201
  {"event_type": "zzprobe_050_not_an_event"}    -> 400 {"event_type": ["event_type is not valid"]}
  {"event_type": ["Shotgun_User_Login"]}        -> 400 {"event_type": ["event_type must be a string"]}
  {"event_type": ""}                            -> 400 {"event_type": ["event_type must be filled"]}
  event_type AND entity_types together          -> 400
     {"entity_types": ["entity_types either entity types or event type is required"]}
  12 of the 39 documented custom events, from Shotgun_User_Login to CRS_Version_Media_Download,
  Shotgun_PermissionRuleSet_ChangeRule and Shotgun_ActionMenuItem_Triggered  -> 201, all of them

the lifecycle actions
  {"Shot": {"create": []}}   201     {"Shot": {"revive": []}}      201
  {"Shot": {"update": []}}   201     {"Shot": {"retire": []}}      400 entity_types is not valid
  {"Shot": {"delete": []}}   201     {"Shot": {"zzprobe_050": []}} 400 entity_types is not valid
  all four in one hook       201

the entities the guide excludes
  ApiUser 201   EventLogEntry 201   AssetShotConnection 201   PermissionRuleSet 201
  HumanUser 201   Project 201   Attachment 201   Note 201

  batch_deliveries=True, validate_ssl_cert=False -> 201, both read back unchanged, status active

63 hooks before, 63 after, the set unchanged
```

**Teaches**

- **The two modes are exclusive, and one message covers both ways of getting it wrong.**
  `entity_types either entity types or event type is required` is returned for a body with neither and
  for a body with both. Read it as "exactly one of these", not as "you are missing one".
- **Every entity the guide calls excluded is accepted at 201.** A hook on `ApiUser`, on
  `EventLogEntry`, or on a connection entity such as `AssetShotConnection` is created, is `active`, and
  reads back intact. The documentation says it will never fire. Nothing in the API says so, so the
  create is not the place you will find out.
- `revive` is a fourth lifecycle action alongside `create`, `update` and `delete`, and it is the
  counterpart to the logical delete in `040_field_revive`. `retire` is not an action: the API spells
  the same operation `delete`.
- **A bogus `event_type` does not enumerate the legal ones.** `event_type is not valid` names nothing,
  unlike the filter operators, which answer a bogus relation with the full list (`017_filter_operators`).
  The 39 custom events are readable from the guide and from nowhere in the API.
- Type errors on `event_type` are specific where the value error is not: a list answers
  `must be a string` and an empty string answers `must be filled`.
- `batch_deliveries` and `validate_ssl_cert` round-trip on create and are readable back.

**Python equivalent**

```python
# probe 050: a login hook, which entity_types cannot express
c.post("/webhook/hooks", json={"url": URL, "event_type": "Shotgun_User_Login"})
```
