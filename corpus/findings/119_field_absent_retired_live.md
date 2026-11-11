---
tags: [schema, custom-field, error-handling, permission, discovery]
endpoints: [POST /schema/<Type>/fields/<field>, PUT /schema/<Type>/fields/<field>, DELETE /schema/<Type>/fields/<field>, GET /schema/<Type>/fields/<field>, POST /schema/<Type>/fields, GET /schema/permission_groups, GET /schema/permission_groups/<code>/entity_types/<Type>, GET /schema/permission_groups/<code>/entity_types/<Type>/fields]
phase: schema
scope: api
measured: sample project 1 of 1, sandbox project written, 2026-11-10; no name spent, one field revived
coverage: partial
unmeasured: a schema write by a person below Admin, and the permission groups as anyone but the script. Both need that person's session; none was available. Blocked on the site.
verdict: Revive is 204 only on a retired field: 404 `Retired field ... does not exist.` on an unused name, 400 `... is not retired.` on a live one. A retired field is a 404 to GET, PUT and DELETE.
---

# 119_field_absent_retired_live

**Q** What do revive, update and retire answer on a name that was never used, on a retired field and
on a live one, and does a project-scoped `visible` write take its project anywhere but the body or
the query?

**Endpoint** `POST, PUT, DELETE /schema/<Type>/fields/<field> ; GET /schema/permission_groups`

**Docs claim** `/spec.json` documents the revive with no error responses, and names three
`/schema/permission_groups` reads.

**Actual**

```
a name never used
POST .../sg_zzprobe_119_never_used  {"revive": true}  or  ?revive=true -> 404 code 103
  "title": "Not Found", "detail": "Retired field Version.sg_zzprobe_119_never_used does not exist."
GET, PUT (any body), DELETE -> 404 code 103
  "detail": "Field 'Version.sg_zzprobe_119_never_used' does not exist."

a retired field
GET, PUT description, PUT visible with project_id, DELETE -> 404 code 103
  "detail": "Field 'Version.sg_zzprobe_115_visibility' does not exist."
POST /schema/Version/fields  text, the display name that derives it -> 400
  {"errors":[{"id":"...","status":400,"code":105,"title":"API schema_field_create() failed, there
   is a retired field with the same field_name: sg_zzprobe_115_visibility. Delete the retired field
   forever from the Trash Page in Shotgun and try again.","source":{"field_name":"there is a retired
   field with the same field_name: sg_zzprobe_115_visibility"},"detail":null,"meta":null}]}

the same field, live
POST {"revive": true} -> 204, empty body
POST {"revive": true}  or  ?revive=true, while live -> 400 code 103
  "title": "Field Version.sg_zzprobe_115_visibility is not retired."     record identical after

GET /schema/permission_groups, as the script -> 200, 1 group
  {"code": "api_admin", "display_name": "API Admin", "entity_type": "ApiUser", ...}
GET /schema/permission_groups/api_admin/entity_types/Version -> 200
  "permissions": {"see": true, "create": true, "retire": true, "update_field_generic": true},
  "actions": {"read": {"access": "allowed"}, "create": ..., "update": ..., "retire": ..., "delete": ...}
```

**One call, three states**

| call | never used | retired | live |
|---|---|---|---|
| `GET` | 404 `Field 'T.f' does not exist.` | 404, the same | 200 |
| `PUT`, any properties | 404, the same | 404, the same | 200 or a 400 |
| `DELETE` | 404, the same | 404, the same | 204 |
| `POST` with `revive` | 404 `Retired field T.f does not exist.` | 204, empty body | 400 `Field T.f is not retired.` |
| `POST /schema/<Type>/fields` deriving that name | 201 | 400 code 105, `source.field_name` set | 201 for `<name>_1` (probe 019) |

Only the revive and the create tell a retired name from an unused one. The revive does it without
creating anything.

**The retired-name refusal** is status 400, `code` 105, and the only create error with
`source.field_name`. Match on `source.field_name`, or on `retired field with the same field_name: `
in `title`, and read the name after the colon: it is the programmatic name, which probe 117 shows can
differ from the one predicted.

**Where a `visible` write takes its project**

| form | result |
|---|---|
| `project_id` in the JSON body, beside `properties` | 200, applied to that project |
| `?project_id=` in the query | 200, applied to that project |
| `project_id` inside the property object | 400 code 104 `The 'visible' property requires a project to be updated.` |
| `"project": {"type": "Project", "id": N}` in the body | 400 code 104, the same |

The project-scoped read takes `?project_id=` in the query (probe 115).

**Permission**

`GET /schema/permission_groups` returned the caller's own group, `api_admin`, and no `HumanUser`
group: `/spec.json` says a caller without `set_permissions` sees only its own. The entity read reports
`see`, `create`, `retire` and `update_field_generic` on rows. Nothing in either response is about
changing the schema. The field read lists `see` and `update` per field, 73 on Version.

What a person below Admin gets from a create, update, retire or revive of a field was not measured.

**Teaches**

| do | why |
|---|---|
| Treat a revive 404 as "nothing to revive" and a 400 `is not retired` as "already live" | a 204 was only ever returned for a retired field, and the live field was unchanged |
| Detect a retired name from `source.field_name` on a 400 code 105 | no read distinguishes retired from unused |
| Treat a 404 on an update as "gone", retired or never there | the two are the same response |
| Do not look in `/schema/permission_groups` for the right to change the schema | it describes rows and field values |
