---
endpoint: POST <links.complete_upload>
tags: [upload, attachment, async, silent]
scope: api
measured: sandbox project written
verdict: Step three, at 201 with a body of a single space. Not JSON, and it never names the row it created, so parsing it crashes after the write has landed.
---

# POST <links.complete_upload>

**Params**

| part | value |
|---|---|
| URL | `links.complete_upload` from step one. It already has `/api/v1` on it; do not prefix it again |
| `upload_info` | the whole `data` object from step one |
| `upload_data` | `{}` is accepted |

**Sample requests**

```python
r = c.post(links["complete_upload"], json={"upload_info": info, "upload_data": {}})
print(r.status_code, repr(r.text))
# 201 ' '
```

One byte, a single space. `r.json()` raises `JSONDecodeError` on it, and the row has already been
created by the time it does. Never parse this reply.

The row it made is only visible on the parent:

```python
c.get("/entity/notes/10963", params={"fields": "attachments"}).json()["data"]["relationships"]
```

```json
{ "attachments": { "data": [ { "id": 2626, "name": "probe041.txt", "type": "Attachment" } ] } }
```

**Response codes**

| status | when |
|---|---|
| 201 | recorded, whether or not step two ever ran |
| 404 | the URL was prefixed twice, with `source: null` |

**Edge cases**

- A 201 here proves the handshake completed, not that bytes exist. With step two skipped the row is
  identical and the stored object is empty.
- The 404 for a double-prefixed URL has `source: null`, which reads as "a Note is not a valid upload
  target" rather than "your URL is wrong".
- For a media field the value is not readable yet: transcoding is asynchronous and the field returns a
  placeholder under `/images/status/transient/` until it finishes.

**Links**

- `endpoints/put_links_upload`
- `endpoints/get_entity_type_id_field_upload`
- `findings/039_upload_silent_failures`
- `findings/024_read_after_write`
- `recipes/006_media_round_trip`