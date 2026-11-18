---
tags: [custom-field, project, permission, sudo, write]
endpoints: [PUT /entity/<type>/<id>, GET /entity/<type>/<id>, POST /entity/<type>/_search, GET /schema/<Type>/fields/<field>, GET /schema/permission_groups, GET /schema/permission_groups/<code>/entity_types/<Type>]
phase: write
scope: api
measured: sandbox project written, 2026-11-17; the script, two Admins and two Artists via sudo; one text field on Project
coverage: partial
unmeasured: Manager and Vendor writes; rights read, not exercised. Blocked on the site: impersonation on for one of each, then `159 --write`
verdict: An Admin updates a custom field on a Project, member or not. An Artist in the project reads it and gets 400 code 104 `The field is not editable for this user` on a PUT; outside it, 404 on the read.
---

# 159_project_field_update_rights

**Q** Who may update a custom field on a Project, and who may read it?

**Endpoint** `PUT /entity/projects/<id> ; GET /entity/projects/<id> ; GET /schema/Project/fields/<field>?project_id=`

**Docs claim** Silent. Probes 094 and 143 measured an Artist on Task, Shot and custom slots.

**Actual**

```
rights on Project, read by the Admin person from GET /schema/permission_groups/<code>/entity_types/Project
  admin     read allowed  create allowed  update allowed  update exceptions null
  manager   read allowed  create allowed  update allowed  update exceptions {"allow": ["users"], "deny": ["user"]}
  artist    read allowed  create denied   update denied   update exceptions {"allow": ["current_user_favorite"], "deny": []}
  vendor    read allowed  create denied   update denied   update exceptions null

each caller on the sandbox Project: schema editable, GET, PUT of the field
  script               editable true   GET reads the value   PUT 200
  Admin, not a member  editable true   GET reads the value   PUT 200
  Admin, a member      editable true   GET reads the value   PUT 200
  Artist, a member     editable false  GET reads the value   PUT 400
    {"status": 400, "code": 104, "title": "The field is not editable for this user: [Project.sg_zzprobe_159_rights]."}
  Artist, not a member editable false  GET 404 {"code": 104, "title": "Not Found", "detail": "Project: <id> not found"}
    PUT 400 {"status": 400, "code": 104, "title": "Entity can not be accessed by this user."}
  _search [field is <value>]: 1 row for each caller, 0 for the Artist who is not a member
```

**Who may write a Project's custom field**

| caller | read | write |
|---|---|---|
| script | yes | 200 |
| Admin, member of the project or not | yes | 200 |
| Artist, member | yes | 400 code 104 `The field is not editable for this user: [Project.<field>].` |
| Artist, not a member | 404, the Project is not visible | 400 code 104 `Entity can not be accessed by this user.` |
| Manager | not measured; the rights table reads update allowed | not measured |
| Vendor | not measured; the rights table reads update denied | not measured |

Every refused write left the value unchanged.

**Teaches**
- Settings an Artist must read and an Admin writes fit a Project field: an Artist who is a member
  reads it with a plain `GET`. An Artist cannot save them; route that write through an Admin or the script.
- Per caller `editable` in `GET /schema/Project/fields/<field>?project_id=` predicted every answer
  (probe 094). Read it to grey out a settings screen before the PUT.
- Project membership gates an Artist's read: outside the project the Project is a 404, so a field
  on it cannot be read either.
- The Manager row allows `update`, but a rights table can still refuse what it lists (probe 094).
  Treat Manager as unknown until measured.
