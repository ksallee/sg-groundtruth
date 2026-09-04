---
tags: [multipart, upload, etag, storage]
endpoints: [GET /entity/<type>/<id>/<field>/_upload, GET /entity/<type>/<id>/<field>/_upload/multipart, POST /entity/<type>/<id>/<field>/_upload, POST /entity/<type>/<id>/<field>/_upload/multipart_abort]
phase: upload
scope: api
measured: sandbox project written, one Version, one Note, two Attachments, all deleted
verdict: `multipart_upload=true` on the init sets `upload_id` and adds `links.get_next_part`. Every part but the last must be at least 5 MiB, and completion needs an `etags` array inside `upload_info`.
---

# 044_multipart_upload

**Q** What changes in the upload handshake when one PUT is not enough?

**Endpoint** `GET /entity/<type>/<id>/<field>/_upload?multipart_upload=true ; GET .../_upload/multipart ; POST .../_upload ; POST .../_upload/multipart_abort`

**Docs claim** The spec declares `multipart_upload` an optional query parameter on both init forms,
`links.get_next_part` present only when it is true, and `etags` required inside `upload_info` for an
S3 multipart completion. It declares the abort body as `{"upload_info": ..., "upload_data": ...}`.

**Actual**

```
init, no parameter    {"upload_id": null, "multipart_upload": false}
                      links: ['complete_upload', 'upload']
init, multipart=true  {"upload_id": "<152 chars>", "multipart_upload": true}
                      links: ['complete_upload', 'get_next_part', 'upload']

parts [10]           -> 201   this_file 200, 10 bytes
parts [1024, 1024]   -> 400   Error completing multipart upload.
parts [5242879, 17]  -> 400   Error completing multipart upload.
parts [5242880, 17]  -> 201   this_file 200, 5242897 bytes

complete with etags omitted -> 400
{"title": "'multipart_upload' is True but no 'etags' send with request.",
 "source": {"etags": "missing and required for multipart uploads."}}

POST .../multipart_abort  {"upload_info": {...}, "upload_data": {}} -> 400
{"timestamp": ["timestamp is missing"], "upload_type": ["upload_type is missing"],
 "upload_id": ["upload_id is missing"], "storage_service": ["storage_service is missing"],
 "original_filename": ["original_filename is missing"]}
POST .../multipart_abort  <the upload_info object, flat>           -> 204, empty body
POST .../multipart_abort  the same upload a second time           -> 400
{"title": "Failed to abort S3 multipart upload"}

GET .../_upload/multipart  every parameter but upload_id -> 400
{"title": "Could not generate upload url. Check the site settings."}
GET .../_upload/multipart  upload_id=nope                -> 200, a presigned links.upload
```

**Teaches**

- The switch is a query parameter on the init, not a file size. Nothing in the API refuses a
  single-PUT upload for being large, so a client decides for itself when to split.
- **The init opens the S3 upload.** `upload_id` is non-null the moment `multipart_upload=true`
  returns, before any byte moves. An init you neither complete nor abort leaves an open multipart
  upload on storage that nothing in Flow PT lists. Abort every init you abandon.

  | parts sent | completion |
  |---|---|
  | one part, any size | 201 |
  | 5242880 bytes then 17 | 201 |
  | 5242879 bytes then 17 | 400 `Error completing multipart upload.` |
  | 1024 bytes then 1024 | 400 `Error completing multipart upload.` |

  5242880 is 5 MiB, the S3 floor on every part but the last. The 400 does not say so. A one-part
  multipart upload is legal and has no floor, so the smallest transfer that exercises the whole flow
  is a single part of a few bytes.
- Walk `links.get_next_part`, do not build it. Each call answers with the next part's `upload` and
  the `get_next_part` after it, incrementing `part_number`. The chain is the only thing that knows
  which part is next.
- Collect the `ETag` response header of every part PUT, in order, and send them as
  `upload_info.etags` at completion. `upload_info` is otherwise the init reply verbatim.
- The abort takes the `upload_info` object **flat at the top level**, not wrapped in `upload_info`.
  The wrapped body the spec declares returns 400 naming all six keys as missing.
