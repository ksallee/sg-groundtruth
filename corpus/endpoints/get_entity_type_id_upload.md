---
endpoint: GET /entity/<type>/<id>/_upload
coverage: measured
tags: [upload, attachment, provenance]
scope: api
measured: sandbox project written
verdict: The same handshake with the field left out of the path, which stores the bytes as an Attachment on `attachment_links` rather than on a field. The type must actually have that field.
---

# GET /entity/<type>/<id>/_upload

`GET /entity/notes/<id>/attachments/_upload` is the fieldless form: `attachments` is the multi_entity
link, not a media field, and the upload lands as an Attachment row on `attachment_links`.

**Params**

| part | value |
|---|---|
| path | `/entity/<type>/<id>/attachments/_upload` |
| `filename` | required, as on the field form |

**Sample requests**

```python
r = c.get("/entity/notes/10963/attachments/_upload", params={"filename": "probe041.txt"})
info, links = r.json()["data"], r.json()["links"]
```

```json
{
  "data": {
    "timestamp": "2026-09-04T03:54:36Z",
    "upload_type": "Attachment",
    "upload_id": null,
    "storage_service": "s3",
    "original_filename": "probe041.txt",
    "multipart_upload": false
  },
  "links": {
    "upload": "<media-url>",
    "complete_upload": "/api/v1/entity/notes/10963/attachments/_upload"
  }
}
```

`upload_type` is `Attachment` here where the field form returns `Thumbnail`. That is the only difference
in the reply.

On a type with no such field:

```json
{"errors": [{"status": 404, "code": 103, "title": "Not Found",
             "detail": "Field 'Shot.attachments' does not exist."}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | `/attachments/_upload`: the type has an `attachments` field. With no segment at all, `/entity/<type>/<id>/_upload`: every type probe 123 tried, Shot and Version included |
| 400 | `filename is missing` |
| 404 | `Field 'Shot.attachments' does not exist.` on `/attachments/_upload` when the type has no such field. Of the stock types probed only Note has one; Version does not (probe 123) |

**Edge cases**

- Not every type has `attachments`. Shot and Version do not, and the 404 names the field rather than
  the route, which is the useful half. Leave the segment out instead: `/entity/<type>/<id>/_upload`
  answers 200 on those types, and the completed file links through `Attachment.attachment_links`
  (probes 014, 123).
- The Attachment row is created by step three, not by this call. Read the parent's `attachments` back to
  learn its id; nothing in this reply names it.

**Links**

- `endpoints/put_links_upload`
- `endpoints/post_links_complete_upload`
- `entity_types/Attachment`
- `findings/014_attach_file`