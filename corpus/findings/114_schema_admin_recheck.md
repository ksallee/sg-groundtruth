---
tags: [schema, custom-entity, custom-field, status-list, discovery, error-handling]
endpoints: [PUT /preferences/custom_entity/<entity_type>/activation, GET /preferences/custom_entity/<entity_type>/configuration, PUT /preferences/custom_entity/<entity_type>/configuration, PUT /preferences/update, POST /schema/<Type>/fields/<field>, DELETE /schema/<Type>/fields/<field>, PUT /schema/<Type>/fields/<field>, GET /schema/<Type>/fields]
phase: schema
scope: api
measured: sample project 1 of 1, sandbox project written, 2026-11-10; one trashed field on Version revived and re-trashed
coverage: partial
unmeasured: a custom entity call that succeeds. The probed site answers 400 code 111 to all three, so the bodies and responses in /spec.json are unverified. Blocked on the site.
verdict: On 2026-11-10 /spec.json names calls to enable, disable and configure a custom entity, all 400 code 111 on the probed site. No call deletes a trashed field forever or writes hidden_values.
---

# 114_schema_admin_recheck

**Q** Has REST gained a way to enable or disable a custom entity, delete a trashed field forever, or
write `hidden_values`?

**Endpoint** `PUT /preferences/custom_entity/<entity_type>/activation ; GET, PUT /preferences/custom_entity/<entity_type>/configuration ; POST, DELETE, PUT /schema/<Type>/fields/<field>`

**Docs claim** The published reference names none of the custom entity calls. `/spec.json` names all
three, and now documents the revive, with `revive` as a query parameter.

**Actual**

```
GET /spec.json: 49 paths, 68 operations (probe 042 recorded 44 and 62)
  forever: nowhere   trash: nowhere   purge: nowhere   hidden_values: nowhere

GET /preferences/custom_entity/CustomEntity01/configuration -> 400
  {"status": 400, "code": 111,
   "title": "Custom entity configuration through the API is not available", "source": null}
PUT /preferences/custom_entity/NotAnEntityType/activation  {"enabled": true} -> 400  same error
PUT /preferences/custom_entity/CustomEntity50/configuration  {} -> 400  same error

DELETE /schema/Version/fields/sg_zzprobe_040_revive -> 404
  "detail": "Field 'Version.sg_zzprobe_040_revive' does not exist."
POST /schema/Version/fields/sg_zzprobe_040_revive  {"revive": false} -> 400
  "source": {"revive": ["revive must be true"]}
POST /schema/Version/fields/sg_zzprobe_040_revive?revive=true -> 204

PUT /schema/Task/fields/sg_status_list
  {"properties": [{"property_name": "hidden_values", "value": [...]}], "project_id": N} -> 400
  "title": "API schema_field_update() invalid property 'hidden_values': ...
   Valid property names: [\"name\", \"visible\", \"description\", \"summary_default\",
   \"default_value\", \"valid_values\", \"custom_metadata\"]"
```

**The three operations**

| operation | 2026-11-10 |
|---|---|
| enable a custom entity | `PUT /preferences/custom_entity/<entity_type>/activation` with `{"enabled": true}` is in `/spec.json`. 400 code 111 on the probed site |
| disable a custom entity | the same call with `{"enabled": false}`, and `force` for a slot that has records. Same 400 |
| read or set a slot's display name and feature flags | `GET` and `PUT /preferences/custom_entity/<entity_type>/configuration`. Same 400 |
| the older `PUT /preferences/update` | unchanged: 400 code 111 `Updating the preferences is not available`, to `disable_entity` as well |
| delete a trashed field forever | no call. Nothing in `/spec.json`, and every guess below was refused |
| list trashed fields | no call. Six more option spellings each returned the live fields only |
| write `hidden_values` | refused by name, with or without `project_id`, in the body or the query |

**The custom entity calls are refused before anything is read**

On the probed site the 400 is identical for an enabled slot, a slot absent from `/schema`, `Shot`, a
type that does not exist, a body with no keys and a complete one. `/spec.json` gives 403
`Custom entity configuration feature is not enabled` for the gated case. The site answers 400 code 111.

| call | status |
|---|---|
| `GET .../<enabled slot>/configuration` | 400 code 111 |
| `GET .../<absent slot>/configuration` | 400 code 111 |
| `GET .../Shot/configuration` | 400 code 111 |
| `GET .../NotAnEntityType/configuration` | 400 code 111 |
| `PUT .../NotAnEntityType/activation` with `{"enabled": true}` | 400 code 111 |
| `PUT .../<absent slot>/activation` with `{}` | 400 code 111 |
| `PUT .../<absent slot>/configuration` with `{}` | 400 code 111 |
| `PUT .../<enabled slot>/configuration` with `{}` | 400 code 111 |
| `GET /preferences/custom_entity` | 404 |
| `GET .../<absent slot>/activation` | 404 |

**Delete forever, guessed, on a field already in the trash**

| sent | result |
|---|---|
| `DELETE` | 404 `Field 'Version.<name>' does not exist.` |
| `DELETE` with `?forever=true`, `?permanent=true` or `?delete_forever=true` | 404, same |
| `DELETE` with a body of `{"forever": true}` or `{"delete_forever": true}` | 404, same |
| `POST` with `{"revive": false}` | 400 `revive must be true` |
| `POST` with `{"delete_forever": true}` | 400 `revive is missing` |
| `DELETE ?forever=true` on the field once revived | 204. It is trashed, and the name is still taken |

**Teaches**

| do | why |
|---|---|
| Read `/spec.json` after a release | it named three calls that no release note or reference page mentioned |
| Treat 400 code 111 from a custom entity call as "not available on this site" | it precedes validation, so it says nothing about the body or the slot |
| Keep sending users to the web interface to enable a slot or empty the field trash | neither can be done over REST on the probed site |
| Send `revive` in the query or in the body | both are a 204 |
| Do not write `hidden_values` | the update lists its seven valid property names and it is not one |
