---
tags: [permission, sudo, custom-entity, attachment, write]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, DELETE /entity/<type>/<id>, GET /schema/permission_groups/<code>/entity_types/<Type>]
phase: write
scope: api
measured: sandbox project written, 2026-11-11; an Admin and an Artist via sudo, five custom slots; 10 rows, 4 Attachments
coverage: partial
unmeasured: Manager and Vendor writes; rights read, not exercised. Blocked on the site: impersonation on for one of each in the sandbox, then `143 --write`
verdict: On the probed site an Artist may not create, edit or delete custom-entity rows (status only) and may create but not delete an Attachment, its own included. The group rights call predicts each answer.
---

# 143_nonadmin_rows

**Q** May a person who is not an administrator create, update and delete rows of the project's custom
entities, and delete an Attachment?

**Endpoint** `POST /entity/<type> ; PUT /entity/<type>/<id> ; DELETE /entity/<type>/<id> ; GET /schema/permission_groups/<code>/entity_types/<Type>`

**Docs claim** Silent. Probe 094 measured an Artist on Task and Shot.

**Actual**

```
as the Artist, on each of the five enabled custom slots (all five answered alike)
  create                          -> 400 code 104 "Entity of type CustomEntityNN cannot be created by this user."
  update code on the script's row -> 400 code 104 "The field is not editable for this user: [CustomEntityNN.code]."
  update sg_status_list           -> 200
  delete the script's row         -> 400 code 104 "Entity of type CustomEntityNN can not be deleted by this user."
  POST /entity/attachments {project, description} -> 201, project set
  delete that Attachment          -> 400 code 104 "Entity of type Attachment can not be deleted by this user."
  delete the script's Attachment  -> 400, the same
as the Admin person: every create, update and delete above -> 201, 200, 204
```

**Rights by group**, read by the Admin person from `GET /schema/permission_groups/<code>/entity_types/<Type>`
on the probed site. The five custom slots read identically. `update exceptions` is `actions.update.field_exceptions`.

| group | type | read | create | update | retire | delete | update exceptions |
|---|---|---|---|---|---|---|---|
| admin | custom slot | allowed | allowed | allowed | allowed | allowed | allow `sg_status_list` |
| admin | Attachment | allowed | allowed | allowed | allowed | allowed | deny `attachable` |
| manager | custom slot | allowed | allowed | allowed | allowed | allowed | allow `sg_status_list`, deny `user` |
| manager | Attachment | allowed | allowed | allowed | allowed | allowed | deny `user`, `attachable` |
| artist, and the Artist variant | custom slot | allowed | denied | denied | denied | denied | allow `sg_status_list` |
| artist, and the Artist variant | Attachment | allowed | allowed | denied | denied | denied | none |
| vendor | custom slot | allowed | denied | denied | denied | denied | allow `sg_status_list` |
| vendor | Attachment | conditional | allowed | conditional | denied | denied | allow `attachment_links`, `project` |

**Teaches**
- Read the caller's own group with `GET /schema/permission_groups` then `.../entity_types/<Type>`
  before writing: every Artist answer above matched the table, the `sg_status_list` exception
  included. A person sees only their own group; an Admin sees all.
- A refusal is a 400 code 104 naming the type or the field, as on Task and Shot (probe 094).
- On the probed site a capture app run by an Artist cannot make its own rows on custom entities and
  cannot remove a photo it uploaded. Either the people get Manager, the site's Artist rules change,
  or the app writes through a script key.
- Manager's rights were read, not exercised; a conditional rule can still refuse a write the table
  lists as allowed (probe 094).
