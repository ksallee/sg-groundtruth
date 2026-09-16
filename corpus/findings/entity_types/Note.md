---
tags: [attachment, jsonb, destructive, note]
scope: api
measured: first sample project read, sandbox project written
summary: A comment about something, with a subject, a body and a thread of replies.
verdict: A Note is titled by `subject` and bodied by `content`; only `project` is required to create one, `attachments` link in that same call, and a bare write to `replies` destroys the Reply rows.
---

# Note

**Type** Schema name `Note`, addressed at `/api/v1/entity/notes`. The slug is neither case nor plural
sensitive, and only an unknown name is refused.

```
GET /entity/notes  -> 200      GET /entity/Note   -> 200
GET /entity/note   -> 200      GET /entity/notess -> 404 "Entity type 'notess' does not exist."
```

Project-scoped. `Note.project` is an editable `entity` field, `valid_types: ['Project']`, and a create
without it is refused. An unfiltered `_search` returns notes from every project, so filter on project.

**Identity** `subject`, display name `Subject`, `data_type: text`, the only field flagged `mandatory`
and none is flagged `unique`. A client shows it as the note's title. The body is `content`, display name
`Body`, also `text`; `Task.content` is display name `Task Name` and is Task's identity
(`entity_types/Task`), so the same field name is a title on one type and a body on the other.

| filter | result |
|---|---|
| `["subject", "is_not", null]` | matches |
| `["content", "is_not", null]` | matches |
| `["cached_display_name", "is_not", null]` | matches |
| `["code", "is_not", null]` | 400 `API read() Note.code doesn't exist.` |
| `["name", "is_not", null]` | 400 `API read() Note.name doesn't exist.` |

`cached_display_name` copies neither: it is `subject` alone when `content` is empty and
`"<subject> - <content>"` when both are set. A `PUT` to it returns 200 and changes nothing (probe 004).

**Create** `POST /entity/notes`, `Content-Type: application/json`. `project` is the whole contract and
the field flagged `mandatory` is optional, as on Asset, Task and Version (probe 012).

| body sent | result |
|---|---|
| `{}` | 400 `API create() missing 'project' attribute: {}` |
| `{"subject": "..."}` | 400, the same title with the body echoed |
| `{"content": "..."}` | 400, the same |
| `{"note_links": [{"type": "Shot", "id": N}]}` | 400, the same |
| `{"project": {"type": "Project", "id": N}}` | 201, no `subject` in the response at all |
| `project` + `subject` | 201 |
| `project` + `subject` + `content` | 201 |
| `project` + `subject` + `note_links` | 201, the link stored |
| `project` + `subject` + `attachments` | 201, the link stored |
| `project` + `client_note: true` | 400 `API create() Client Notes can not be created through the API`, as the script and under `sudo_as_login` alike |
| `project` + `client_note: false` | 201; the 201 echo omits the key and a re-read returns `false` |
| `project` + `created_at: "2019-03-04T05:06:07Z"` | 201, stored as sent, though the schema flags it `editable: false` (probe 070) |

An omitted `subject` is not auto-filled, unlike `Asset.code` and `Task.content`: the row has no title.
The 201 echoes the server's defaults, so read them off the response:

```json
{"cached_display_name": "", "sg_status_list": "opn", "publish_status": "published",
 "read_by_current_user": "unread", "created_at": "...", "updated_at": "...",
 "reply_content": "Warning: If you see this displayed in the UI, it means the widget is not
  respecting grid_column = false."}
```

`user` and `created_by` both hold the authenticating script's `ApiUser`, and every link field is `[]`.

**Links** Written and read as described in `field_types/entity` and `field_types/multi_entity`.

| field | type | valid_types | editable |
|---|---|---|---|
| `project` | entity | `['Project']` | yes |
| `user` | entity | `['HumanUser', 'ApiUser']` | yes |
| `playlist` | entity | `['Playlist']` | yes |
| `notes_app_context` | entity | `['Playlist', 'CutItem', 'Cut']` | yes |
| `composition` | entity | `['Composition']` | yes |
| `created_by` | entity | `['HumanUser', 'ApiUser', 'ClientUser']` | no |
| `updated_by` | entity | `['HumanUser', 'ApiUser']` | no |
| `image_source_entity` | entity | every entity type on the site | no |
| `note_links` | multi_entity | the reviewable types, below | yes |
| `replies` | multi_entity | `['Reply']` | yes |
| `attachments` | multi_entity | `['Attachment']` | yes |
| `tasks` | multi_entity | `['Task']` | yes |
| `tags` | multi_entity | `['Tag']` | yes |
| `addressings_to`, `addressings_cc` | multi_entity | `['Group', 'HumanUser']` | yes |

`note_links` attaches a Note to the thing it is about. `Task` is absent: a Note about a Task goes in the separate `tasks` field. On the probed site `valid_types` holds 28 entries, 26 stock and two `CustomEntityNN`:

```
Asset, Booking, Camera, Contract, Cut, Department, Episode, Group, Launch, Level, MocapPass,
MocapSetup, MocapTake, MocapTakeRange, Performer, Playlist, Reel, Routine, Scene, Sequence,
ShootDay, Shot, Slate, SourceClip, TaskTemplate, Version
```

Search "notes about X" through the link: it filters although it cannot be read back (probe 016), and the path names the target type, which decides the name field (probe 071).

| path, over the 28 valid types | resolves | `is "sh010"` |
|---|---|---|
| `note_links.<Type>.cached_display_name` | 28 of 28 | 20 rows |
| `note_links.<Type>.code` | 27; `note_links.Booking.code` 400s `doesn't exist` | the same 20 |
| `note_links.<Type>.name` | 1, `Department`; the other 27 400 | |
| `note_links.Shot.sg_sequence.Sequence.code` | yes, two hops resolve | |
| `note_links`, bare, with `contains` | 400 `'multi_entity' data type doesn't support 'contains' 'relation'` | |

The list is not enforced either, and
creates sending `[{"type": "Project", ...}]` and `[{"type": "HumanUser", ...}]` both returned 201 and
read the link back. Starting from `[Shot, Asset]`:

| `PUT /entity/notes/<id>` | result |
|---|---|
| `{"note_links": [Shot]}` | 200, `[Shot]`; the Asset link is gone |
| `{"note_links": {"multi_entity_update_mode": "add", "value": [Asset]}}` | 200, `[Shot, Asset]` |

**Threading** The link is stored on the Reply, in `Reply.entity`. `Note.replies` is the reverse view,
and writing it destroys rows rather than unlinking them. `entity_types/Reply` covers the other end.

| call | result |
|---|---|
| `POST /entity/replies {"entity": {"type": "Note", "id": N}, "content": "..."}` | 201; the Note then reads `replies: [{id, name, type: "Reply"}]` |
| `POST /entity/replies {"content": "..."}` | 201 with `entity` null, an unattached Reply |
| `PUT /entity/notes/N {"replies": []}` | 200; the Reply is gone, and `_search` on its id returns 0 rows |
| `DELETE` that Reply afterwards | 404 `Entity of type [Reply] with id=514 does not exist.` |
| `DELETE` an unattached Reply | 400 `Delete failed for [Reply with id=515]: undefined method 'reflect_on_association' for class NilClass` |
| `PUT` an `entity` onto that Reply, then `DELETE` | 200, then 204 |

**Attachments** An Attachment links in the same call that creates the Note; no second pass is needed.
`POST /entity/attachments {"project": {...}}` returns 201 for an empty row, and probe 014 uploads a file.

| call | result |
|---|---|
| `POST /entity/notes` with `attachments: [{"type": "Attachment", "id": N}]` | 201, stored, and a re-read returns it |
| `PUT /entity/notes/N {"attachments": [...]}` on an existing Note | 200 |
| `PUT /entity/attachments/N {"attachment_links": [{"type": "Note", "id": M}]}` | 200, the same link from the other side |

**Status** `sg_status_list`, a `status_list`, holding a raw code and never a label. Read a project's
usable set as `valid_values` minus `hidden_values`, which writes do not enforce
(`field_types/status_list`); the vocabulary and both lists are site configuration.

```
GET /schema/Note/fields/sg_status_list?project_id=<pid>
  -> properties.valid_values.value, .hidden_values.value, .display_values.value
```

`default_value` applies when the key is omitted on create, so a Note is never statusless. The
`open_notes_count` rollup on other types counts Notes whose status is in the site's open set and can be
neither filtered nor sorted (`field_types/summary`).

**Read state** `read_by_current_user` holds `"read"` or `"unread"` per authenticated identity and is in no schema response: `GET /schema/Note/fields` returns 33 fields without it, and `GET /schema/Note/fields/read_by_current_user` answers 200 with `data: null` (probe 068).

| call | result |
|---|---|
| `PUT {"read_by_current_user": "read"}` as the script | 200, re-reads `"unread"`: an ApiUser has no read state |
| the same `PUT` under `sudo_as_login` | 200, re-reads `"read"` for that person and `"unread"` for everyone else |
| `"zzznope"` | 400 `Update failed for [Note.read_by_current_user]: 'zzznope' is not a valid list value. Valid list values: 'read', 'unread'.` |
| `["read_by_current_user", "is", "unread"]` | the caller's unread Notes |
| `["read_by_current_user", "in", ["read"]]` | 200 and the caller's unread Notes; the filter is not evaluated |

**Traps**
- **`client_note` cannot be set over the API**, on create or after. Every update answers `400 API update() Note.client_note is editable on create only.` A client-facing Note over REST is `sg_note_type: "Client"`, an editable `list`, and nothing else; it leaves `client_note` false (probe 069).
- **A bare `replies: []` write deletes the Reply rows.** Trimming that list the way a client trims any
  other `multi_entity` field destroys the replies, with nothing at the id after. Keep it out of a `PUT`.
- A bare list written to `note_links` replaces the set, so appending one link with
  `[{"type": "Shot", "id": N}]` drops every other thing the Note was about
  (`field_types/multi_entity`).
- `subject` is optional, not auto-filled and not unique: a request that dropped its payload creates a
  real titleless Note, and two Notes in one project may share a subject. Key on `id`.
- `meta` is editable on create only. Seed it in the `POST` or never: every later `PUT` answers
  `400 API update() Note.meta is editable on create only.` (`field_types/jsonb`).
