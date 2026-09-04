---
endpoint: GET /entity/notes/<id>/thread_contents
coverage: measured
tags: [note, reply, attachment, user]
scope: api
measured: sample project 1 of 1
verdict: A Note, its Attachments and its Replies as one flat list in time order. The Note and the Attachments name their author under `created_by`, a Reply names it under `user`.
---

# GET /entity/notes/<id>/thread_contents

Only `notes` has this path. It replaces one `_search` on Note plus one on Reply plus one on
Attachment, and it orders the three together.

**Params**

| part | value |
|---|---|
| `<id>` | a Note id |
| `entity_fields[<Type>]` | comma-separated extra fields for rows of that type |

**Sample requests**

```python
r = c.get("/entity/notes/6376/thread_contents")
```

```json
{
  "data": [
    {"type": "Note", "id": 6376, "content": "<note body>",
     "created_at": "2025-05-30T20:39:17Z",
     "created_by": {"id": 88, "name": "<user>", "type": "HumanUser"}},
    {"type": "Attachment", "id": 650,
     "created_at": "2025-05-30T20:39:19Z",
     "created_by": {"id": 88, "name": "<user>", "type": "HumanUser"}},
    {"type": "Reply", "id": 477, "content": "<reply body>",
     "created_at": "2025-05-30T21:21:50Z",
     "user": {"id": 88, "name": "<user>", "type": "HumanUser", "image": "<media-url>"}}
  ],
  "links": {"self": "/api/v1/entity/notes/6376/thread_contents"}
}
```

```python
r = c.get("/entity/notes/6376/thread_contents",
          params={"entity_fields[Note]": "sg_status_list,subject",
                  "entity_fields[Reply]": "updated_at",
                  "entity_fields[Attachment]": "filename"})
```

```
Note        ['content', 'created_at', 'created_by', 'id', 'sg_status_list', 'subject', 'type']
Attachment  ['created_at', 'created_by', 'filename', 'id', 'type']
Reply       ['content', 'created_at', 'id', 'type', 'user']
```

**Response codes**

| status | when |
|---|---|
| 200 | the thread, one row minimum: the Note itself |
| 404 | `detail: "Note: 999999999 not found"` |
| 404 | `detail: "Field 'Version.thread_contents' does not exist."` on any other type |

**Edge cases**

The author key changes with the row type, and so does what `entity_fields` can add:

| row type | author under | `entity_fields` widened it |
|---|---|---|
| `Note` | `created_by` | yes |
| `Attachment` | `created_by` | yes |
| `Reply` | `user` | no |

- A Reply's `user` hash has a fourth key, `image`, a presigned avatar URL re-signed per read. The
  `created_by` hash on the other two rows has no `image`.
- `entity_fields[Reply]` was accepted and changed nothing, so extra Reply fields need a
  `POST /entity/replies/_search`.
- `content` is absent from an Attachment row. Only its id, type, timestamp and author are returned
  unless `entity_fields[Attachment]` asks for more.
- A Note with no replies answers one row, its own, at 200.
- The 404 for another type is worded as a missing field rather than a missing route, which is what
  distinguishes it from a bad id.

**Links**

- `entity_types/Note`
- `entity_types/Reply`
- `endpoints/get_entity_type_id_activity_stream`
- `findings/043_attention`
