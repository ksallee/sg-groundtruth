---
endpoint: GET /entity/<type>/<id>/_upload/multipart
tags: [multipart, attachment]
scope: api
measured: sandbox project written, one Note whose multipart init was aborted, all rows deleted
verdict: The fieldless part chain, `/entity/<type>/<id>/attachments/_upload/multipart`. Same four checked parameters and the same unchecked `upload_id` as the field form.
---

# GET /entity/<type>/<id>/_upload/multipart

`endpoints/get_entity_type_id_upload` returns `links.get_next_part` when called with
`multipart_upload=true`, exactly as the field form does. Follow the chain; nothing about it differs
from `endpoints/get_entity_type_id_field_upload_multipart` except the path and the `upload_type` the
init settled on.

**Params**

| part | value |
|---|---|
| path | `/entity/<type>/<id>/attachments/_upload/multipart`, from `links.get_next_part` verbatim |
| `filename`, `upload_type`, `timestamp`, `part_number` | required and checked |
| `upload_id` | required and unchecked |

**Sample requests**

```python
b = c.get("/entity/notes/10965/attachments/_upload",
          params={"filename": "notes.pdf", "multipart_upload": "true"}).json()
sorted(b["links"])
# ['complete_upload', 'get_next_part', 'upload']
b["data"]["upload_type"]
# 'Attachment'
```

```json
{"links": {
  "upload": "<media-url>",
  "get_next_part": "/api/v1/entity/notes/10965/attachments/_upload/multipart?filename=notes.pdf&part_number=3&timestamp=2026-09-04T04%3A41%3A49Z&upload_id=<152 chars>&upload_type=Attachment"}}
```

**Response codes**

| status | when |
|---|---|
| 200 | a presigned URL for that part |
| 400 | `source` naming any of `filename`, `upload_type`, `timestamp`, `part_number` |
| 400 | `Could not generate upload url. Check the site settings.` when `upload_id` is absent |
| 404 | `Field 'Shot.attachments' does not exist.` on a type without the field |

**Edge cases**

- `upload_type` is `Attachment` on this form and `Thumbnail` on `image`. Send back whatever the init
  returned; the chain rejects nothing else.
- The 5 MiB floor on every part but the last is the same here. See `findings/044_multipart_upload`.

**Links**

- `endpoints/get_entity_type_id_upload`
- `endpoints/get_entity_type_id_field_upload_multipart`
- `endpoints/post_entity_type_id_upload`
- `endpoints/post_entity_type_id_upload_multipart_abort`
- `findings/044_multipart_upload`