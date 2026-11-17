---
tags: [schema, custom-field, multi-entity, on-set, shot]
endpoints: [POST /schema/<Type>/fields, GET /schema/<Type>/fields, GET /schema/<Type>/fields/<field>, DELETE /schema/<Type>/fields/<field>, POST /entity/<type>, PUT /entity/<type>/<id>, POST /entity/_batch, POST /entity/<type>/_search]
phase: schema
scope: api
measured: site-wide schema write, 2026-11-17; one Slate field and its reverse retired; a Slate and 3 Shots in the sandbox, deleted
verdict: A multi_entity `<field>` on Slate to Shot makes `slate_<field>_slates` on Shot, editable and visible; by that rule `sg_shots` gives `slate_sg_shots_slates`. A link written at either end reads at both.
---

# 155_slate_shots_reverse

**Q** A custom multi_entity field on Slate with `valid_types: ["Shot"]`: what reverse field does the
server add on Shot, and does a link written from either end read back from the other?

**Endpoint** `POST /schema/Slate/fields ; GET /schema/Shot/fields ; POST /entity/slates ; POST /entity/_batch ; PUT /entity/shots/<id>`

**Docs claim** Silent. Probe 142 measured the rule between two custom slots only.

**Actual**

```
POST /schema/Slate/fields multi_entity, name "zzprobe 155 shots", valid_types ["Shot"] -> 201
  forward  Slate.sg_zzprobe_155_shots   valid_types ['Shot']
  new on Shot, the only new field:
           slate_sg_zzprobe_155_shots_slates   multi_entity, name 'Slates <-> zzprobe 155 shots',
           valid_types ['Slate'], editable True, visible True

POST /entity/slates {sg_zzprobe_155_shots: [S1]}       -> 201; S1's reverse field [the slate]
_batch update, mode add [S2] (probe 154)               -> 200; Slate [S1, S2]; S2's reverse [the slate]
PUT S3 {slate_sg_zzprobe_155_shots_slates: [the slate]} -> 200; Slate [S1, S2, S3]
Shots ["slate_sg_zzprobe_155_shots_slates", "is", <slate>] -> [S1, S2, S3]

DELETE /schema/Slate/fields/sg_zzprobe_155_shots       -> 204
GET /schema/Shot/fields/slate_sg_zzprobe_155_shots_slates after -> 404, retired with it
```

**Teaches**
- The reverse name is `<source slug, singular>_<field>_<source slug, singular>s`, as probe 142 found on
  custom slots: for Slate, `slate_<field>_slates`. By that rule `sg_shots` gets `slate_sg_shots_slates`.
  Its display name is `<source display name, plural> <-> <field display name>`.
- It is one link with two names. Write it from the Slate or from the Shot and it reads back at both;
  filter Shots by the reverse field to find a Slate's Shots without reading the Slate.
- Retiring the forward field retired the reverse with it (probe 142). Both names stay taken until the
  Trash page is emptied. This probe used the `sg_zzprobe_155_` prefix, so `sg_shots` is still free.
