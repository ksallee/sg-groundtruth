---
tags: [schema, custom-field, project, write, error-handling]
endpoints: [GET /schema/<Type>/fields, GET /schema/<Type>/fields/<field>, PUT /schema/<Type>/fields/<field>, GET /schema, POST /schema/<Type>/fields/<field>]
phase: schema
scope: api
measured: sample project 1 of 1, sandbox project written, 2026-11-10; one text field on Version, retired
verdict: `visible` is per project. Read it with `?project_id=N`; write it with PUT and `project_id` in the body or the query, never without one. A new field is visible in every project.
---

# 115_field_visibility_per_project

**Q** Is a field's `visible` a per-project value, and can it be read and written for one project
without touching the others?

**Endpoint** `GET /schema/<Type>/fields?project_id=N ; GET, PUT /schema/<Type>/fields/<field>`

**Docs claim** `/spec.json` gives the PUT body an optional `project_id`, "which project to modify the
`visible` property for", and the reads a `project_id` query parameter. It does not say `visible` is
unwritable without one.

**Actual**

```
GET /schema/Shot/fields              100 fields, 64998 bytes, visible false: 0
GET /schema/Shot/fields?project_id=N (sandbox)   100 fields, 65042 bytes, visible false: 12
GET /schema/Shot/fields?project_id=M (sample 1)  100 fields, 65027 bytes, visible false: 15
  hidden in the sandbox only: 6, in sample 1 only: 9, in both: 6
GET /schema/Shot/fields/<field>?project_id=M -> visible {"value": false, "editable": false}
GET /schema/Shot/fields/<field>?project_id=999999999 -> 200, visible true

POST /schema/Version/fields  text, 'zzprobe 115 visibility' -> 201  sg_zzprobe_115_visibility
  visible, site / sandbox / sample 1: {"value": true, "editable": true} at all three

PUT .../sg_zzprobe_115_visibility  {"properties": [{"property_name": "visible", "value": false}]}
  -> 400 code 104 "API schema_field_update(): The 'visible' property requires a project to be updated."
PUT  {"properties": [{"property_name": "visible", "value": false}], "project_id": N}
  -> 200, the whole field   site: true   sandbox: false   sample 1: true
PUT ...?project_id=N  {"properties": [{"property_name": "visible", "value": true}]}
  -> 200                    site: true   sandbox: true    sample 1: true
PUT  {"properties": [...visible false...], "project_id": 999999999}
  -> 400 code 105 "API schema_field_update(): The Project with the given project_id does not exist."

DELETE while hidden in the sandbox -> 204 ; POST {"revive": true} -> 204
  visible after the revive: true at site, sandbox and sample 1
```

**Read**

| call | returns |
|---|---|
| `GET /schema/<Type>/fields` | every field, `visible.value` true: the site scope holds no hidden field |
| `GET /schema/<Type>/fields?project_id=N` | every field of the type with that project's `visible.value`, in one call |
| `GET /schema/<Type>/fields/<field>?project_id=N` | the same value for one field |
| either, with a `project_id` that does not exist | 200, and every `visible.value` true |
| `GET /schema?project_id=N` | each entity type's own `visible`, also per project |

A hidden field is returned, with `visible.value` false. The key is never absent: on the probed site
all 227 fields of Version, Shot and Task have `visible` at every scope.

**Write**

| sent | result |
|---|---|
| `visible`, no project | 400 code 104 `The 'visible' property requires a project to be updated.` |
| `visible`, `project_id` in the JSON body | 200, that project only |
| `visible`, `?project_id=` in the query | 200, that project only |
| `visible`, `project_id` inside the property object (probe 119) | 400 code 104, the same message |
| `visible`, `"project": {"type": "Project", "id": N}` in the body (probe 119) | 400 code 104, the same message |
| `visible` with the value the project already holds | 200 |
| `visible` as the string `"false"` | 200, hidden |
| `visible` with a `project_id` that does not exist | 400 code 105 `The Project with the given project_id does not exist.` |
| `visible` and `description` in one PUT with `project_id` | 200. `visible` for that project, `description` for the site |
| `description` alone with `project_id` | 200, changed for the site |

After every write the site-scope reading and the sample project were unchanged.

**Teaches**

| do | why |
|---|---|
| Read one type's visibility per project with one listing call | `?project_id=N` returns `visible` for all its fields |
| Treat a new field as visible everywhere | it reads true at site scope and in both projects straight after the create |
| Send `project_id` with every `visible` write | without it the write is a 400, and there is no site-wide write |
| Check the project id yourself before a read | a wrong id reads as "everything visible" at 200; only the write refuses it |
| Write visibility again after a revive | a field hidden in a project, retired and revived, came back visible there |
| Do not use `visible` to protect data | the hidden field was still returned by `GET /entity/versions?fields=` in that project |

Probes 118 and 119 repeat the write on a custom entity type and on Tag, which has no `project` field:
the same.
