---
endpoint: POST /entity/<type>/<id>/_upload/multipart_abort
coverage: measured
tags: [multipart, note]
scope: api
measured: sandbox project written, one Note whose multipart init was aborted, all rows deleted
verdict: The fieldless abort, `/entity/<type>/<id>/attachments/_upload/multipart_abort`. 204 on the flat `upload_info` object, identical to the field form in every respect but the path.
---

# POST /entity/<type>/<id>/_upload/multipart_abort

**Params**

| part | value |
|---|---|
| path | `/entity/<type>/<id>/attachments/_upload/multipart_abort`. Not in `links`; append it to the init path |
| body | the init reply's `data` object, flat at the top level |

**Sample requests**

```python
b = c.get("/entity/notes/10965/attachments/_upload",
          params={"filename": "notes.pdf", "multipart_upload": "true"}).json()
c.post("/entity/notes/10965/attachments/_upload/multipart_abort", json=b["data"])
# 204 ''
```

The wrapped body, as on the field form:

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
  "source": {"timestamp": ["timestamp is missing"], "upload_type": ["upload_type is missing"],
             "upload_id": ["upload_id is missing"], "storage_service": ["storage_service is missing"],
             "original_filename": ["original_filename is missing"]}}]}
```

**Response codes**

| status | when |
|---|---|
| 204 | aborted. Empty body |
| 400 | `Request Parameters invalid.` for the `{"upload_info": ..., "upload_data": ...}` wrapper |
| 400 | `Failed to abort S3 multipart upload` when there is no open upload under that `upload_id` |
| 404 | `Field 'Shot.attachments' does not exist.` on a type without the field |

**Edge cases**

- `endpoints/post_entity_type_id_field_upload_multipart_abort` holds the edge cases; both forms
  answered identically at every input measured.

**Links**

- `endpoints/get_entity_type_id_upload`
- `endpoints/get_entity_type_id_upload_multipart`
- `endpoints/post_entity_type_id_upload`
- `endpoints/post_entity_type_id_field_upload_multipart_abort`
- `findings/044_multipart_upload`