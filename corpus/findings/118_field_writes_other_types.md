---
tags: [schema, custom-field, custom-entity, create, project]
endpoints: [POST /schema/<Type>/fields, PUT /schema/<Type>/fields/<field>, DELETE /schema/<Type>/fields/<field>, POST /schema/<Type>/fields/<field>, GET /schema/<Type>/fields/<field>]
phase: schema
scope: api
measured: sample project 1 of 1, sandbox project written, 2026-11-10; one text field on two types
coverage: partial
unmeasured: a CustomNonProjectEntityNN. None is enabled on the probed site. Blocked on the site.
verdict: Create, update, per-project `visible`, retire, the retired-name 400 and revive answer on a custom entity and on Tag, which has no `project` field, exactly as on Version.
---

# 118_field_writes_other_types

**Q** Do create, per-project `visible`, retire, the retired-name refusal and revive behave on a custom
entity type and on a type with no `project` field as they do on Version?

**Endpoint** `POST /schema/<Type>/fields ; PUT, DELETE, POST /schema/<Type>/fields/<field>`

**Docs claim** Silent. The reference documents the calls for any entity type.

**Actual**

```
enabled CustomEntityNN: 2, CustomNonProjectEntityNN: 0

CustomEntityNN, 26 fields, has a `project` field: True
POST /schema/CustomEntityNN/fields  text, name 'zzprobe 118 other type', description -> 201
  links.self /api/v1/schema/custom_entityNN/fields/sg_zzprobe_118_other_type
  visible  site: true  sandbox: true  sample 1: true
PUT visible false, project_id sandbox -> 200    site: true  sandbox: false  sample 1: true
PUT description -> 200, reads back changed
DELETE -> 204 ; GET -> 404 ; listed: False
POST the same display name -> 400 code 105
  "API schema_field_create() failed, there is a retired field with the same field_name:
   sg_zzprobe_118_other_type. Delete the retired field forever from the Trash Page in Shotgun and
   try again."
POST {} to the field path -> 400  source {"revive": ["revive is missing"]}
POST {"revive": true} -> 204 ; GET -> 200, data_type text, the changed description

Tag, 8 fields, has a `project` field: False
  every line above, identical, with links.self /api/v1/schema/tag/fields/sg_zzprobe_118_other_type
```

**Teaches**
- The same programmatic name, `sg_zzprobe_118_other_type`, was created on both types: a name is taken
  per entity type, not per site.
- `links.self` spells the type in snake case, `custom_entityNN` and `tag`, where Version's reads
  `Version`. Take the last segment for the field name and do not parse the type out of it.
- Per-project `visible` works on a type that has no `project` field. Hiding the Tag field in the
  sandbox left the site scope and the sample project reading true.
- On the probed site the custom entity is project-scoped and Tag is stock. A `CustomNonProjectEntityNN`
  was not available to measure.
