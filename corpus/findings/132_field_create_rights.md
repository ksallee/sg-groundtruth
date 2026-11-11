---
tags: [schema, custom-field, permission, sudo, error-handling]
endpoints: [POST /schema/<Type>/fields, PUT /schema/<Type>/fields/<field>, DELETE /schema/<Type>/fields/<field>, POST /schema/<Type>/fields/<field>, GET /schema/permission_groups, GET /schema/permission_groups/<code>/entity_types/<Type>]
phase: schema
scope: api
measured: site-wide, 2026-11-11; the script, an Admin and an Artist via sudo; two fields created on a custom slot and retired
coverage: partial
unmeasured: Manager, Vendor and the site's Artist variant: nobody active in them has impersonation on. Blocked on the site; then run `132 --write --only Manager,Vendor`
verdict: An Artist creating a field gets 500 code 105 `User doesn't have permission to create a Field`, with a traceback. An Admin person gets 201. Treat any 500 from a schema write as a possible refusal.
---

# 132_field_create_rights

**Q** What does `POST /schema/<Type>/fields` answer a caller who is not an administrator, and which
permission groups may create fields?

**Endpoint** `POST /schema/<Type>/fields ; PUT /schema/<Type>/fields/<field> ; DELETE /schema/<Type>/fields/<field> ; GET /schema/permission_groups/<code>/entity_types/<Type>`

**Docs claim** Silent on who may change the schema. `/spec.json` describes the permission group calls
as row rights.

**Actual**

```
POST /schema/CustomEntityNN/fields {"data_type": "text", name "zzprobe 132 <group>"}
  Admin person -> 201 sg_zzprobe_132_admin
  Artist       -> 500 {"status": 500, "code": 105,
                  "title": "API schema_field_create() RuntimeError: User doesn't have permission to create a Field",
                  "detail": "{traceback: \"/var/rails/shotgun/current/app/models/display_column.rb:2764:in
                             'block in DisplayColumn.create_column'\\n ..."}

a live field the script made, written by the Artist
  PUT description -> 500 code 105 "API schema_field_update() RuntimeError: User doesn't have
                     permission to configure Field properties."   detail null; description unchanged
  DELETE          -> 400 code 104 "User doesn't have permission to retire a Field"; field still live

a name no field holds, Admin and Artist alike
  PUT, DELETE  -> 404 code 103 "Field 'CustomEntityNN.sg_zzprobe_132_absent' does not exist."
  revive       -> 404 code 103 "Retired field CustomEntityNN.sg_zzprobe_132_absent does not exist."

GET /schema/permission_groups?permission_rule_set_entity_type=HumanUser
  script (API Admin) -> []      Admin person -> all 5 groups      Artist -> ['artist']
GET /schema/permission_groups/artist/entity_types/CustomEntityNN, as the Artist
  "permissions": {"see": true, "create": false, "retire": false, "update_field_generic": false, ...}
  no key about fields
```

**Who may create fields**

| caller | create | configure (`PUT`) | retire (`DELETE`) |
|---|---|---|---|
| script, `api_admin` | 201 (probes 019, 116) | 200 | 204 |
| Admin person | 201 | not sent | not sent |
| Artist | 500 code 105 | 500 code 105 | 400 code 104 |
| Manager, Vendor, the Artist variant | not measured | not measured | not measured |

**Teaches**
- The three schema writes refuse in three shapes: create and configure are 500 code 105 with
  `RuntimeError` in the title, retire is 400 code 104. A client retrying 5xx would retry a refusal
  forever; match `doesn't have permission` in the title before retrying.
- Permission is checked after the field is looked up: an absent field is a 404 for the Artist too,
  so a probe on a made-up name tells a caller nothing about its rights.
- No call answers "may I create a field" without trying. The permission group calls describe rows
  only, and an Artist sees only its own group. On the probed site the Admin person read every
  group's row rights (probe 143 lists them); none of them names fields.
- Field creation is a site-administration right on the probed site: Admin yes, Artist no. Whether
  Manager has it was not reachable, so a client should not infer it from Manager's row rights.
