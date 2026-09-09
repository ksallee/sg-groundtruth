---
tags: [entity-field, multi-entity, link, destructive]
endpoints: [GET /entity/<type>/<id>, POST /entity/<type>/_search, PUT /entity/<type>/<id>, POST /entity/<type>, DELETE /entity/<type>/<id>, GET /schema/<Type>/fields/<field>]
phase: read
scope: api
measured: sandbox project written, one row per type
verdict: The `name` in an entity dict is the target's `cached_display_name`, filled on every type measured, single and multi alike. Read it, not the per-type identity field, and expect decoration.
---

# 060_entity_dict_name

**Q** Is `name` in the dict returned for an entity link the target's display name, whatever the target
type is?

**Endpoint** `GET /entity/versions/{id} ; POST /entity/versions/_search ; PUT /entity/versions/{id}`

**Docs claim** Silent. The REST docs show the `{id, name, type}` shape and do not say what fills `name`
or where else it can be read.

**Actual**

```
PUT Version.entity, one type at a time, then GET /entity/versions/{id}
  type        PUT  dict keys     dict name                    identity field                cached_display_name
  Shot        200  id,name,type  "zzprobe_060_shot"           code="zzprobe_060_shot"       "zzprobe_060_shot"
  Task        200  id,name,type  "zzprobe_060_task"           content="zzprobe_060_task"    "zzprobe_060_task"
  Note        200  id,name,type  "zzprobe_060_note"           subject="zzprobe_060_note"    "zzprobe_060_note"
  Project     200  id,name,type  "sandbox"                    name="sandbox"                "sandbox"
  Delivery    200  id,name,type  "#68: zzprobe_060_delivery"  title="zzprobe_060_delivery"  "#68: zzprobe_060_delivery"
  12 more types, each 200, each id,name,type, each equal to the target's cached_display_name

multi_entity, the same PUT and read
  notes      [{"id": 10997, "name": "zzprobe_060_note", "type": "Note"}]
  tasks      [{"id": 46781, "name": "zzprobe_060_task", "type": "Task"}]
  playlists  [{"id": 79, "name": "zzprobe_060_playlist", "type": "Playlist"}]

GET, _search under api3_array and _search under api3_hash: relationships identical, byte for byte

Task, the type with neither a name nor a code
  GET ?fields=cached_display_name          {"cached_display_name": "zzprobe_060_task"}
  GET ?fields=name                         {}
  filter ["name", "is", "x"]               400 API read() Task.name doesn't exist.
  filter ["code", "is", "x"]               400 API read() Task.code doesn't exist.
  filter ["cached_display_name","is","x"]  200

deleted target
  sg_task    {"id": 46784, "name": "zzprobe_060_doomed_task", "type": "Task"}  DELETE 204  reads null
  playlists  [{"id": 82, "name": "zzprobe_060_doomed_playlist", ...}]          DELETE 204  reads []
  entity     DELETE the linked Shot 204, then GET the Version 404; under
             options[return_only]=retired the Version answers 200 with entity null
```

**Teaches**

**`name` is `cached_display_name`, not the identity field.** Every type `Version.entity` accepts on the
probed site, plus the three a client reaches through another field. One row per type, each created in
the sandbox and linked with a single `PUT`.

| target type | identity field | dict `name` equals |
|---|---|---|
| Asset, Level, MocapTake, Reel, ShootDay, Shot, Sequence, Launch, Camera, Slate, SourceClip | `code` | the identity field |
| the site's two enabled CustomEntity slots (probe 008) | `code` | the identity field |
| Task, reached through `sg_task` or written into `entity` | `content` | the identity field |
| Note, reached through `notes` or written into `entity` | `subject` | the identity field |
| Project, reached through `project` | `name` | the identity field |
| Delivery | `title` | `cached_display_name`, which is `#<id>: <title>` |

Sixteen of the seventeen agree with the identity field because `cached_display_name` is a copy of it.
Delivery is the one that does not, and it is what a client renders in a picker, so read
`cached_display_name` and never reconstruct the identity field from it.

**It is the one type-agnostic name.** `name` was present and populated in all 17 dicts, and never `null`
except when the row itself was gone. A client holding a link needs no second call and no per-type map of
`code` against `content` against `subject`.

| where the link comes back | element shape |
|---|---|
| `entity`, `sg_task`, `project`, `user`, `created_by` | `{id, name, type}` |
| `notes`, `tasks`, `playlists`, `sg_ai_generated_from` | a list of `{id, name, type}` |

`multi_entity` elements are the same three keys with the same `name` (`field_types/multi_entity`).

**Headers change nothing.** `GET /entity/versions/{id}`, `POST _search` under
`application/vnd+shotgun.api3_array+json` and the same `_search` under `...api3_hash+json` returned
byte-identical `relationships` blocks, confirming probe 004 on the dict's contents.

**`cached_display_name` is readable, not filter-only.** `?fields=cached_display_name` and a `_search`
`fields` list both answered it on Task, Shot, Asset, Project, Version and Note, and it matched the dict
`name` in each. Task is the case that matters: the dict's `name` and the field `cached_display_name` are
the only two ways to name a Task, since `name` and `code` do not exist on it (`entity_types/Task`).

| asked for | Task, Shot, Asset, Version, Note | Project |
|---|---|---|
| `?fields=cached_display_name` | the display name | the display name |
| `?fields=name` | 200, `attributes` empty | 200, `name`, a real field |
| `["name", "is", "x"]` as a filter | 400 `API read() <Type>.name doesn't exist.` | matches |

`?fields=name` is the silent drop probe 004 records: a client that asks for `name` on a Version gets 200
and nothing, which reads as "no display name" rather than "wrong field".

**A gone target is dropped, never stale.** Nothing holds a dead `{id, name, type}`.

| the link | after the target is deleted |
|---|---|
| `sg_task` | `data` is `null` |
| `playlists` and every other `multi_entity` measured | the element is removed from the list |
| `entity`, when the target is the Shot the Version hangs off | the Version itself is retired |
| a filter on any of the three, against the deleted id | 200, 0 rows |

- **Destructive.** `DELETE /entity/shots/{id}` returned 204 and retired every Version linked to that Shot
  through `entity`: the Version answered 404 on a `GET`, 0 rows in `_search`, and 200 with `entity` null
  under `options[return_only]=retired`. Deleting a Task or a Playlist retires only itself. Read the
  children before deleting a parent; the 204 names nothing it took with it.
