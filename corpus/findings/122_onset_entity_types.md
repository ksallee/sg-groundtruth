---
tags: [on-set, schema, create, link, custom-entity, discovery]
endpoints: [GET /schema, GET /schema/<Type>, GET /schema/<Type>/fields, GET /entity/<type>, POST /entity/<type>, PUT /entity/<type>/<id>, GET /preferences, GET /preferences/custom_entity/<entity_type>/configuration, PUT /preferences/custom_entity/<entity_type>/configuration, PUT /preferences/custom_entity/<entity_type>/activation]
phase: schema
scope: api
measured: site-wide schema read; sandbox project written, 2026-11-11, 21 rows made and deleted
coverage: partial
unmeasured: a stock site, and enabling a hidden type: Element is off on the probed site and only the web UI turns a type on. Blocked on the site
verdict: Slate, Camera, MocapTake, ShootDay and Scene create like Version: `project` required, `code` generated. None has `attachments`, and only Version.entity and Note.note_links reach them all.
---

# 122_onset_entity_types

**Q** Are the built-in on-set types (Slate, Camera, MocapTake, ShootDay, Scene, Element) there, what
does each take to create, and how do they link to Shot and Version? Can a custom entity slot be
enabled or renamed by API?

**Endpoint** `GET /schema ; GET /schema/<Type>/fields ; POST /entity/<type> ; PUT /entity/<type>/<id> ; GET, PUT /preferences/custom_entity/<entity_type>/configuration`

**Docs claim** Silent. The REST reference names no entity type and does not say how a type is
turned on.

**Actual**

```
GET /schema   Slate, Camera, MocapTake ("Mocap Take"), ShootDay ("Shoot Day"), Scene: listed,
              visible {"value": true, "editable": false}
              Element: absent. /schema lists AssetElementConnection and ElementShotConnection
GET /schema/Element/fields -> 404 code 103 "Entity type 'Element' does not exist."
GET /entity/elements       -> 404 code 103 "Entity type 'elements' does not exist."

GET /entity/mocap_takes 200   /entity/MocapTake 200   /entity/mocaptakes 404
GET /entity/shoot_days  200   /entity/ShootDay  200   /entity/shootdays  404

POST /entity/slates {}                  -> 400 code 103 "API create() missing 'project' attribute: {}"
POST /entity/slates {"code": ...}       -> 400 code 103 "API create() missing 'project' attribute: ..."
POST /entity/slates {"project": ...}    -> 201 code "New Slate <id>", sg_status_list "wtg"
  identical for cameras ("New Camera <id>"), mocap_takes ("New Mocap Take <id>"),
  shoot_days ("New Shoot Day <id>"), scenes ("New Scene <id>")

POST /entity/versions entity=<Slate|Camera|MocapTake|ShootDay>  -> 201, reads back that type
POST /entity/versions entity=<Scene>  (not in valid_types)      -> 201, reads back Scene
PUT  /entity/shots/<id> sg_scene=<Slate> (valid_types [Scene])   -> 200
PUT  Shot.sg_scene=<Scene> -> Scene.shots holds the Shot; PUT Scene.shots -> Shot.sg_scene set
POST /entity/notes note_links=[<each of the five>]              -> 201

GET  /preferences/custom_entity/<enabled slot>/configuration -> 400 code 111
GET  /preferences/custom_entity/Slate/configuration          -> 400 code 111
PUT  .../NotAnEntityType/configuration {"display_name": ...}  -> 400 code 111
  "Custom entity configuration through the API is not available"
```

**Stock fields**, by probe 056's rule (`visible.editable` false). Every other field on these types is
the site's own: on the probed site Slate has 63 fields, 45 of them the site's.

| type | stock fields beyond the common set | `sg_status_list` valid on the probed site |
|---|---|---|
| Slate | none | `wtg ip cmpt` |
| Camera | `mocap_takes` | `wtg ip cmpt` |
| MocapTake | `assets`, `cameras`, `performers`, `physical_assets`, `sg_routine`, `sg_scene`, `task_template`, `tasks`, `step_0` | `wtg ip cmpt` |
| ShootDay | `assets`, `performers`, `scenes`, `task_template`, `tasks`, `step_0` | `wtg ip cmpt pnddel pcd` |
| Scene | `addressings_cc`, `assets`, `cuts`, `launches`, `shoot_days`, `shots`, `sg_scene_type` | `wtg ip fin` |

The common set on all five: `code` (text, flagged mandatory, generated when omitted), `project`,
`description`, `image`, `filmstrip_image`, `notes`, `open_notes`, `tags`, `sg_status_list`, and the
server-managed `created_*`, `updated_*`, `cached_display_name`, `image_blur_hash`, `image_source_entity`.
None has `attachments`.

**Links to Shot and Version**, stock fields only

| field | reaches |
|---|---|
| `Version.entity` | Slate, Camera, MocapTake, ShootDay in `valid_types`; Scene also accepted at 201 |
| `Note.note_links` | all five |
| `Shot.sg_scene` / `Scene.shots` | Scene only, one link read from both ends |
| `Task.entity` | MocapTake, ShootDay |
| `Attachment.attachment_links` | ShootDay, Scene. Not Slate, Camera, MocapTake |

A stock Slate has no field naming a Shot or a Version. On the probed site each type also has a
`sg_versions` multi_entity ("Version <-> Link") that lists a Version once its `entity` names the row;
that field is the site's, not stock.

**Teaches**
- Create every on-set row with `project`; `code` is optional and `"New <Display Name> <id>"` when
  omitted, exactly as Version (entity_types/Version).
- `/schema` is the switch: a hidden built-in type is absent from it and 404s by name everywhere,
  while its connection types stay listed. No API call turns it on; the 400 code 111 of probe 114
  answers for stock types and renames too, so plan for an admin turning the type on in the web interface (not measured: no setting was changed).
- Link a take to its Shot through a Version (`Version.entity`) or a site field; stock Slate has no
  Shot link. `valid_types` is not enforced on `Version.entity` or `Shot.sg_scene`
  (field_types/entity), so check the type on the client.
- `mocap_takes` and `shoot_days` are the slugs: the CamelCase name also resolves, the run-together
  plural does not.
