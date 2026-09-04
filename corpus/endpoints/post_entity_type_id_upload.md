---
endpoint: POST /entity/<type>/<id>/_upload
tags: [multipart, attachment, note]
scope: api
measured: sandbox project written, one Note whose multipart init was aborted, all rows deleted
verdict: The fieldless completion, `/entity/<type>/<id>/attachments/_upload`. Same body contract as the field form, including `etags` for a multipart init; the row lands on `attachment_links`.
---

# POST /entity/<type>/<id>/_upload

`attachments` in the path is the multi_entity link rather than a media field, so the completed upload
becomes an Attachment on `attachment_links`. `endpoints/get_entity_type_id_upload` mints the links.

**Params**

| part | value |
|---|---|
| path | `/entity/<type>/<id>/attachments/_upload`, from `links.complete_upload` verbatim |
| `upload_info` | the init reply's `data` object, verbatim |
| `upload_info.etags` | required when the init returned `multipart_upload: true` |
| `upload_data` | `{}`, or `display_name` and `tags` |

**Sample requests**

```python
b = c.get("/entity/notes/10965/attachments/_upload",
          params={"filename": "notes.pdf", "multipart_upload": "true"}).json()
# links: ['complete_upload', 'get_next_part', 'upload']
# data:  {"upload_type": "Attachment", "multipart_upload": true, "upload_id": "<152 chars>"}
```

```python
r = c.post(b["links"]["complete_upload"], json={
    "upload_info": dict(b["data"], etags=etags), "upload_data": {}})
# 201 ' '
```

The parent is the only place the new row is named:

```json
{ "attachments": { "data": [ { "id": 2626, "name": "notes.pdf", "type": "Attachment" } ] } }
```

**Response codes**

| status | when |
|---|---|
| 201 | recorded. The body is a single space |
| 400 | `'multipart_upload' is True but no 'etags' send with request.` |
| 400 | `Error completing multipart upload.` |
| 404 | `Field 'Shot.attachments' does not exist.` on a type without the field |

**Edge cases**

- The field form and this one answer identically apart from `upload_type`, `Thumbnail` against
  `Attachment`. Everything in `endpoints/post_entity_type_id_field_upload` applies here unchanged.
- Not every type has `attachments`. Shot does not; Note and Version do.
- Diff the parent's `attachments` before and after to learn the new id. The 201 body is a space.

**Links**

- `endpoints/get_entity_type_id_upload`
- `endpoints/post_entity_type_id_field_upload`
- `endpoints/get_entity_type_id_upload_multipart`
- `endpoints/post_entity_type_id_upload_multipart_abort`
- `findings/044_multipart_upload`