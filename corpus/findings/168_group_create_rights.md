---
tags: [group, permission, sudo, shot, trap]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, DELETE /entity/<type>/<id>, GET /entity/<type>/<id>, GET /schema/<Type>/fields, GET /schema/permission_groups, GET /schema/permission_groups/<code>/entity_types/<Type>, GET /schema/permission_groups/<code>/entity_types/<Type>/fields]
phase: write
scope: api
measured: sandbox project written, 2026-11-21, 3 runs; 18 Groups and 1 Shot each, deleted; 2 people re-roled via sudo, restored
coverage: partial
unmeasured: an App Session Launcher bearer (probe 052); it needs the person to approve at a browser. `sudo_as_login` applies the same permission set (probe 094)
verdict: On the probed site a Manager or Admin person creates, renames, re-members and retires any Group; Artist and Vendor get 400 code 104. The person's own group rights on Group predict each answer.
---

# 168_group_create_rights

**Q** Which permission groups may create, update and retire a Group over REST as a person, does the
rights call predict it, and what does `POST /entity/groups` require?

**Endpoint** `POST /entity/groups ; PUT /entity/groups/<id> ; DELETE /entity/groups/<id> ; GET /schema/permission_groups/<code>/entity_types/Group`

**Docs claim** Silent. Probe 150 created a Group with the script only. `GET /schema/Group/fields`
reads `code` as `mandatory: true`, `unique: false`.

**Actual**

```
person A through sudo_as_login, moved through each group; B is the member added and removed
                                          manager    admin      artist     vendor
own group's rights on Group, actions.create   allowed    allowed    denied     denied
  update / retire / delete                    allowed    allowed    denied     denied
  /fields update on code, users, sg_people    allowed    allowed    denied     denied
GET /schema/Group/fields editable, the same   true       true       false      false
POST {code}                                   201        201        400        400
POST {code, users: [B]}                       201        201        400        400
  created_by is person A; users read back [B]
PUT code, users add B, users remove B         200        200        400        400
  (on A's own Group and on one the script made: the same answers)
DELETE, then GET as the script                204, 404   204, 404   400, 200   400, 200

400 bodies, artist and vendor alike, source, detail and meta null:
  POST    {"status": 400, "code": 104, "title": "Entity of type Group cannot be created by this user."}
  PUT     {"status": 400, "code": 104, "title": "The field is not editable for this user: [Group.code]."}
          the same naming [Group.users] for the users PUTs
  DELETE  {"status": 400, "code": 104, "title": "Entity of type Group can not be deleted by this user."}

POST {users: []}, no code, as a manager      201; code and cached_display_name "New Group <id>"
POST, as the script, the code of a live Group  201, a second Group with the same code
  the same code in upper case                  201
  the code of a Group retired above            201

a Manager's Group holding B (a Vendor), on a sandbox Shot
  B: GET the Shot                              404 code 104 "Not Found" detail "Shot: <id> not found"
  A: PUT sg_vendor_groups {"multi_entity_update_mode": "add", "value": [the Group]}   200
  B: GET the Shot at once                      200, 0.5 to 0.6 s after the write
  script: sg_vendor_groups []; B: GET           404
```

**What each caller reads to learn its own group**

| call, as the person | manager | admin | artist | vendor |
|---|---|---|---|---|
| `GET /schema/permission_groups?permission_rule_set_entity_type=HumanUser` | `['manager']` | all five | `['artist']` | `['vendor']` |
| own `HumanUser.permission_rule_set` | `Manager` | `Admin` | `Artist` | `Vendor` |
| `GET /entity/permission_rule_sets/<that id>?fields=code` | `manager` | `admin` | `artist` | `vendor` |

**Teaches**
- Check before showing the control: read the person's own `permission_rule_set`, its `code`, then
  `actions.create.access` on Group. An Admin lists every group, so the listing alone does not name theirs.
- A refusal is 400 code 104, not 403, with no `source` or `detail`. Probe 094's shape holds for Group.
- The right is per type, not per creator: a Manager renames, re-members and retires a Group someone
  else made, a vendor's included. An app that lets production create Groups lets it retire any Group.
- `code` is neither required nor unique, whatever the schema says. Search by `code` before creating,
  and keep the id: two Groups may share a name. A retired Group drops out of `HumanUser.groups`.
- A Group made by a person works in `Shot.sg_vendor_groups` on the vendor's next request (probe 166).
