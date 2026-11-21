---
tags: [schema, custom-field, project, permission, sudo, error-handling]
endpoints: [POST /schema/<Type>/fields, GET /schema/<Type>/fields/<field>, GET /schema/<Type>/fields, DELETE /schema/<Type>/fields/<field>, GET /entity/<type>/<id>]
phase: schema
scope: api
measured: site-wide, 2026-11-17; an Admin and an Artist via sudo; one text field made on Project and retired
coverage: partial
unmeasured: Manager, Vendor and the Artist variant: nobody active in them has impersonation on. Blocked on the site; then `157 --write --only Manager`
verdict: An Admin person creates a text field on Project with name and description at 201; it reads back like a field on any type. An Artist gets 500 code 105 `User doesn't have permission to create a Field`.
---

# 157_project_custom_field

**Q** Can a custom text field be created on Project over REST, with what body, by whom, and how does it
read back in the schema?

**Endpoint** `POST /schema/Project/fields ; GET /schema/Project/fields/<field> ; GET /entity/projects/<id>`

**Docs claim** `/spec.json` lists `text` among the creatable types and says nothing about Project or about
who may create.

**Actual**

```
POST /schema/Project/fields
  {"data_type": "text", "properties": [{"property_name": "name", "value": "zzprobe 157 admin"},
                                       {"property_name": "description", "value": "zzprobe 157: ..."}]}
  Admin person -> 201 links.self .../schema/Project/fields/sg_zzprobe_157_admin
  Artist       -> 500 {"status": 500, "code": 105,
                  "title": "API schema_field_create() RuntimeError: User doesn't have permission to create a Field",
                  "detail": "{traceback: \"/var/rails/shotgun/current/app/models/display_column.rb:2764:in ..."}

GET /schema/Project/fields/sg_zzprobe_157_admin
  name {"value": "zzprobe 157 admin", "editable": true}   description {"value": "zzprobe 157: ...", ...}
  data_type "text"   entity_type "Project"   editable true   visible true   mandatory false   unique false
  properties {"default_value": {"value": null, "editable": false}, "summary_default": {"value": "none", ...}}
  ?project_id=<sandbox>, the script   identical to the site read
  ?project_id=<sandbox>, the Artist   editable {"value": false}   visible true
GET /schema/Project/fields            lists it, entry identical to the single read
GET /entity/projects/<sandbox>?fields=sg_zzprobe_157_admin   {"sg_zzprobe_157_admin": null}
GET /entity/projects/<sandbox>        the field among the attributes, with no fields named
GET /schema/Project/fields/sg_onset_templates -> 404 code 103 "Field 'Project.sg_onset_templates' does not exist."
```

**Who may create a field on Project**

| caller | result |
|---|---|
| script, `api_admin` | 201 (probes 158, 159) |
| Admin person | 201 |
| Artist | 500 code 105, traceback in `detail`. Nothing created |
| Manager, Vendor, the Artist variant | not measured: no active person in them has impersonation on |

The answers match probe 132 on a custom slot: Project has no rule of its own for field creation.

**Teaches**
- The body is the same as on any type: `data_type` and a `properties` list holding `name`, plus
  `description` if wanted. The `sg_` name is the last segment of `links.self` (probe 019).
- The display name decides the `sg_` name by probe 117's rule: `Onset Templates` gives
  `sg_onset_templates`, `Onset Reference Kinds` gives `sg_onset_reference_kinds`. A display name in use
  gives `_1` (probe 019) and a retired one is a 400 code 105 until the Trash is emptied (probe 117).
- A Project field is site-wide: `?project_id=` changes nothing for an Admin, and per caller `editable`
  is false for an Artist (probe 159 has the write).
- Match `doesn't have permission` in a 500's title before retrying a schema write (probe 132).
