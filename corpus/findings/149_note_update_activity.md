---
tags: [note, follow, reply, sudo, async]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, GET /entity/<type>/<id>, GET /entity/<type>/<id>/activity_stream, GET /entity/<type>/<id>/followers]
phase: observe
scope: api
measured: sandbox project written, 2026-11-17; one Shot, Task, Note and Reply, all deleted; Note written via sudo_as_login
coverage: partial
unmeasured: the Inbox, which has no REST call, and a launcher bearer. Needs a browser: see the table at the end
verdict: A person's Note create streams at once; a PUT to `content` or `addressings_to` writes no stream row in 150 s but turns the addressee back to unread. An addressee added later follows at once.
---

# 149_note_update_activity

**Q** When a person creates a Note and later updates it, what reaches the activity streams, does the
addressee's read state reset, and is an addressee added later made a follower?

**Endpoint** `POST /entity/notes ; PUT /entity/notes/<id> ; GET /entity/<type>/<id>/activity_stream ; GET /entity/notes/<id>/followers`

**Docs claim** Silent. Probe 067 found a script's Note create absent from every stream and a Note
created under `sudo_as_login` on the Shot's stream within 60 s.

**Actual**

```
Shot; Task on it assigned to B; the Note written by the operator under sudo_as_login
streams polled every 15 s, up to 150 s per step: the Shot, the Note, the Task

1. POST note_links [Shot], tasks [Task], addressings_to [B]  201  followers [B, operator]
   first poll, about 3 s later: create on Shot, Note, Task, created_by HumanUser <operator>
   meta {"type": "new_entity", "entity_type": "Note", "entity_id": <id>,
         "sudo_actual_user": {"type": "ApiUser", "id": <id>, "name": "<script> 1.0", "valid": "valid", "uuid": ...}}
2. B marks it read                                  200  read as B "read", as C "unread"
3. PUT content, as the operator                     200  at once: read as B "unread"
   nothing new on any stream in 150 s
4. PUT addressings_to add C (update mode add)       200  at once: followers [B, C, operator]
   nothing new on any stream in 150 s; read as C "unread"
5. B marks it read; a Reply by the operator         200, 201  at once: read as B "unread"
   first poll: create_reply on Shot, Note, Task, created_by HumanUser <operator>
Note updated_by: the operator
```

**What each write by a person does**

| write | stream row | addressee's read state | followers |
|---|---|---|---|
| Note create | `create`, on the Shot, the Note and the Task, within 3 s | `unread` | the addressees and the author |
| `PUT content` | none in 150 s | back to `unread` at once | unchanged |
| `PUT addressings_to` add C | none in 150 s | C `unread` | C added at once |
| Reply | `create_reply`, on all three, within 3 s | `unread` for B | unchanged |

**Teaches**
- An edited Note is unread again for the people it is addressed to, though no stream row records the
  edit. A feed built from streams misses the update; read the Note's `updated_at`, or its read state
  as the person.
- Adding an addressee later makes them a follower at once, as addressing at create does (probe 147).
- A row written under `sudo_as_login` names the person in `created_by` and the script in
  `meta.sudo_actual_user`, so anyone reading the stream can see a script acted for the person.
- Step 5 marked B read and replied without a read in between; the `unread` after it is the Reply's or
  the mark not holding, and the run does not separate the two.

**Needs a browser**

| question | step |
|---|---|
| does the edited Note come back into B's Inbox, and at the top | run `149 --write --wait 600`, sign in as B in a private window, open the Inbox after step 3 is printed |
| is C notified when added in step 4 | the same run, signed in as C, after step 4 |
