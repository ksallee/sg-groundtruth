---
endpoint: POST /entity/<type>/<id>/<field>/_upload/multipart_abort
tags: [multipart, storage]
scope: api
measured: sandbox project written, one Version, six multipart uploads aborted, all rows deleted
verdict: 204 and an empty body. The body is the `upload_info` object flat at the top level, not the `{"upload_info": ..., "upload_data": ...}` wrapper the spec declares, which returns 400.
---

# POST /entity/<type>/<id>/<field>/_upload/multipart_abort

Every init called with `multipart_upload=true` opens an upload on storage before any byte is sent.
Nothing in Flow PT lists the open ones. An init that is not completed has to be aborted here.

**Params**

| part | value |
|---|---|
| path | the init path with `/multipart_abort` on the end. It is not in `links` |
| body | the init reply's `data` object, **flat**: `timestamp`, `upload_type`, `upload_id`, `storage_service`, `original_filename`, `multipart_upload` |

**Sample requests**

```python
info, links = b["data"], b["links"]
c.post(f"/entity/versions/31850/sg_uploaded_movie/_upload/multipart_abort", json=info)
# 204 ''
```

The wrapper the spec declares:

```python
c.post(path, json={"upload_info": info, "upload_data": {}})
```

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
  "source": {"timestamp": ["timestamp is missing"], "upload_type": ["upload_type is missing"],
             "upload_id": ["upload_id is missing"], "storage_service": ["storage_service is missing"],
             "original_filename": ["original_filename is missing"]}}]}
```

The same six keys as query parameters, no body:

```json
{"errors": [{"status": 400, "code": 103, "title": "No data in request body.", "source": {}}]}
```

Aborting the same upload a second time, and aborting an init that was never multipart:

```json
{"errors": [{"id": 1, "status": 400, "code": 103,
  "title": "Failed to abort S3 multipart upload", "source": {}, "detail": null}]}
```

**Response codes**

| status | when |
|---|---|
| 204 | aborted. Empty body |
| 400 | `Request Parameters invalid.` with the five keys named, for the wrapped body |
| 400 | `No data in request body.` for query parameters alone |
| 400 | `Failed to abort S3 multipart upload` when there is no open upload under that `upload_id` |

**Edge cases**

- The five names in the 400 are the parameters the endpoint wants at the top level. `multipart_upload`
  is not among them and sending the whole `data` object satisfies it either way.
- A completion that failed with `Error completing multipart upload.` leaves the upload open. Abort
  after every failed completion, not only after an abandoned one.
- The abort works on a retired record: deleting the row does not close the upload for you.
- `Failed to abort S3 multipart upload` is the answer for an id that was already aborted, was
  completed, or was never multipart. It does not distinguish them, so a second abort is safe to send
  and its 400 proves nothing was left open.

**Links**

- `endpoints/get_entity_type_id_field_upload`
- `endpoints/get_entity_type_id_field_upload_multipart`
- `endpoints/post_entity_type_id_field_upload`
- `endpoints/post_entity_type_id_upload_multipart_abort`
- `findings/044_multipart_upload`