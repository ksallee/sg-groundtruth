---
tags: [entity-field, multi-entity, link, trap]
endpoints: [PUT /entity/<type>/<id>, GET /entity/<type>/<id>, POST /entity/<type>/_search, GET /entity/<type>/<id>/relationships/<related_field>, DELETE /entity/<type>/<id>, POST /entity/<type>/<id>, POST /entity/<type>, POST /entity/_batch]
phase: write
scope: api
measured: sandbox project written, 2026-11-17; 2 Tasks, 2 Playlists and 1 Version made and deleted, two runs
verdict: A link to a deleted row is hidden, not removed: it reads null or drops out, and returns on revive, even after a replace. A write naming a deleted row is 400 code 104 `Value is not legal.`
---

# 161_link_to_deleted_row

**Q** An entity or multi_entity link whose target row was deleted: what does a read return, does it
come back when the target is revived, and what does a write naming a deleted row answer?

**Endpoint** `PUT /entity/versions/<id> ; DELETE /entity/<type>/<id> ; POST /entity/<type>/<id>?revive=1 ; POST /entity/_batch`

**Docs claim** Silent. Probe 060 measured the read once: `sg_task` null, the element gone from `playlists`.

**Actual**

```
V: sg_task T1, playlists [P1, P2]
DELETE T1, DELETE P1 -> 204, 204
  GET, _search, relationships/playlists   sg_task null   playlists [P2]
  filter sg_task is T1, playlists is P1   0 rows
revive T1, revive P1 -> 200 {"did_revive": true}
  sg_task T1   playlists [P1, P2]
DELETE both again, then writes naming them, V re-read after each
  PUT sg_task = T1 (retired)                -> 400 {"code": 104, "title": "Update failed for [Version.sg_task]: Value is not legal."}
  PUT sg_task = {"type": "Task", "id": 99999999} -> 400, the same
  PUT playlists = [P1]                      -> 400 "Update failed for [Version.playlists]: Value is not legal."
  PUT playlists = [P2, P1]                  -> 400, the same; [P2] unchanged
  PUT playlists add [P1], remove [P1]       -> 400, the same, both
  POST /entity/versions with sg_task = T1   -> 400 {"code": 104, "title": "Invalid field value, update failed
                                               [5 - Update failed for [Version.sg_task]: Value is not legal.]"}
  _batch update sg_task = T1                -> 400 "Update failed for [Version.sg_task]: Value is not legal."
PUT playlists = [P2] while P1 is retired -> 200; revive P1 -> playlists [P1, P2]
```

**Read, by the state of the target**

| target | `entity` field | `multi_entity` field | filter `is <target>` |
|---|---|---|---|
| live | the target | listed | matches |
| deleted | `null` | dropped from the list | 0 rows |
| revived | the target again | listed again | matches |

**Write naming a deleted row**

| write | result |
|---|---|
| `PUT`, entity field | 400 code 104 `Update failed for [<Type>.<field>]: Value is not legal.` |
| `PUT`, multi_entity, bare list, the row alone or beside a live one | the same 400; nothing applied |
| `PUT`, multi_entity, `add` or `remove` | the same 400 |
| `POST` create | 400 code 104 `Invalid field value, update failed [5 - ...Value is not legal.]` |
| `_batch` update | the same 400 as `PUT` |
| `PUT`, entity or multi_entity, an id that never existed | the same 400. A deleted row and a missing one cannot be told apart |

**Teaches**
- **A replace does not drop a hidden link.** On `Version.playlists`, with P1 retired, `[P2]` answered
  200 and read `[P2]`; reviving P1 brought it back. `remove` naming P1 is the same 400, so nothing
  measured removes it. Expect a revive to restore every link to the row. Not measured on an entity field.
- Before writing a link, drop every target the client holds that may have been deleted elsewhere: one
  retired id fails the whole update, the live ones with it.
- `Value is not legal.` also answers a type the field does not take (`field_types/multi_entity`).
  To tell a deleted row from a wrong type, read the target with `options[return_only]=retired`.
