---
tags: [note, reply, task, version, async, silent]
endpoints: [GET /entity/<type>/<id>/activity_stream, POST /entity/<type>, PUT /entity/<type>/<id>]
phase: observe
scope: api
measured: sandbox project written, two runs of five rows each
verdict: A Reply reaches every linked stream in 33 s as `create_reply`, creates too; a script's Note create and status changes were absent after 430 s. Write as a person.
---

# 067_notes_in_the_stream

**Q** Which streams does a Note, a Reply and a status change appear in, and how long after the write?

**Endpoint** `GET /entity/<type>/<id>/activity_stream ; POST /entity/<type> ; PUT /entity/<type>/<id>`

**Docs claim** The REST reference says the stream "corresponds to the data that is displayed in the
Activity tab" and names no latency. Autodesk's Toolkit renderer branches on `create`, `create_reply`
and `update` and logs anything else as unsupported.

**Actual**

```
t+0s   created Shot, Task assigned to the person, Version on both        (script user)
t+2s   Note (note_links Version+Shot, tasks Task, addressed to the person) -> 201
       Reply on it -> 201, Task sg_status_list -> ip 200, Version sg_status_list -> rev 200

polling every 30s
t+33s  Shot stream     4 new: create_reply Note, create Version, create Task, create Shot
t+33s  Task stream     3 new: create_reply Note, create Version, create Task
t+33s  Version stream  2 new: create_reply Note, create Version
t+33s  Project stream  4 new: the same four as the Shot
t+34s  Note stream     1 new: create_reply Note
t+430s HumanUser stream: nothing new (first run, 430 s; second run, 125 s)
never: a `create` for the Note, an `update` for either status change

the create_reply row, verbatim
{"id": 247337, "update_type": "create_reply",
 "meta": {"type": "new_entity", "entity_type": "Reply", "entity_id": 610, "content": "<reply body>"},
 "created_at": "2026-09-15T17:01:53Z", "read": false,
 "primary_entity": {"type": "Note", "id": 11030, "name": "<subject> - <note body>", "status": "opn"},
 "created_by": {"type": "ApiUser", "id": 298, "name": "<script>", "status": null, "image": null}}
```

**Teaches**

- **`create_reply` is a fourth `update_type`**, next to `create`, `update` and `delete`
  (`probe 043`). Its `primary_entity` is the Note, named `<subject> - <content>`, and `meta` holds the
  Reply's id and its `content`, so a feed can draw the reply without a second call.
- One update id is written once and fanned out: the same `create_reply` row, id `247337`, was on
  the Note, the Version, the Shot, the Task and the Project. A fan-out over several streams must
  deduplicate on `id`.
- A record's stream holds the creates of its children: the Shot's had the Task and the Version, the
  Task's had the Version. The Version's stream holds no Task. Read the Shot or Asset, not the Task.
- Latency for what does show is under 33 s on the probed site, against the 90 s absence
  `probe 043` measured. Poll at 30 s.
- A Note created by the script user wrote no `create` row on any of six streams, and two status
  changes by the script wrote no `update`, in 430 s. Attribute changes made in the web application
  are on the same streams.
- Autodesk staff on the community forum tie API-made Inbox items to `sudo_as_login` and to the
  script's "Generate Events" flag. A Note created under `scope=sudo_as_login` on the same site was
  on the Shot's stream and on its own within 60 s. Attribute a write to a person (`probe 027`).
- `read_by_current_user` on the Note read `"unread"` for the script, a string, not a boolean.
