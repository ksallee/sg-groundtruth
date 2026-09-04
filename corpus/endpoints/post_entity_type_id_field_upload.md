---
endpoint: POST /entity/<type>/<id>/<field>/_upload
tags: [multipart, etag, attachment]
scope: api
measured: sandbox project written, one Version and two Attachments, all deleted
verdict: The path behind `links.complete_upload`. `upload_info` is the init reply verbatim, plus an `etags` array when the init was multipart; `upload_data` is where `display_name` and `tags` are set.
---

# POST /entity/<type>/<id>/<field>/_upload

The same path as the init, differing by method. `links.complete_upload` from
`endpoints/get_entity_type_id_field_upload` is this URL, already prefixed with `/api/v1`; post to it
unchanged rather than assembling the path.

**Params**

| part | value |
|---|---|
| `upload_info` | the init reply's `data` object, verbatim. All six keys are required |
| `upload_info.etags` | **required when `multipart_upload` is true.** The `ETag` header of every part PUT, quotes stripped, in part order |
| `upload_data` | `{}`, or `display_name` and `tags` |
| `upload_data.display_name` | sets the Attachment's `display_name` and `cached_display_name`. `filename` and `original_fname` keep the uploaded name |
| `upload_data.tags` | `[{"type": "Tag", "id": <id>}]`. Not measured |
| `filename` | the spec declares it a required query parameter. Completions here omitted it and returned 201 |

**Sample requests**

Single PUT, `upload_info` untouched:

```python
r = c.post(links["complete_upload"], json={"upload_info": info, "upload_data": {}})
# 201 ' '
```

Multipart, with the part ETags and a display name:

```python
etags = [p.headers["ETag"].strip('"') for p in parts]
r = c.post(links["complete_upload"], json={
    "upload_info": dict(info, etags=etags),
    "upload_data": {"display_name": "plate_v003"}})
# 201 ' '
```

```json
{"filename": "zzprobe_044.bin", "original_fname": "zzprobe_044.bin",
 "display_name": "plate_v003", "file_size": null, "file_extension": null}
```

A multipart init completed without `etags`:

```json
{"errors": [{"id": 1, "status": 400, "code": 103,
  "title": "'multipart_upload' is True but no 'etags' send with request.",
  "source": {"etags": "missing and required for multipart uploads."}}]}
```

Parts under the S3 floor, `etags` correct:

```json
{"errors": [{"id": 1, "status": 400, "code": 103,
  "title": "Error completing multipart upload.", "source": {}, "detail": null}]}
```

**Response codes**

| status | when |
|---|---|
| 201 | recorded. The body is a single space |
| 400 | `'multipart_upload' is True but no 'etags' send with request.` |
| 400 | `Error completing multipart upload.` Any part but the last under 5 MiB, or a wrong ETag |
| 404 | the URL was prefixed with `/api/v1` twice, `source: null` |

**Edge cases**

- `Error completing multipart upload.` has an empty `source` and no `detail`. The S3 reason behind it,
  a part below 5 MiB among them, is not passed through.
- A 400 here does not close the upload. The parts stay on storage until
  `endpoints/post_entity_type_id_field_upload_multipart_abort` runs.
- `file_size` and `file_extension` read `null` on a 5 MiB two-part upload that downloads intact, so
  neither separates a completed transfer from an abandoned one.
- The reply is one space and never names the Attachment it made. Read the field back for its `id`.

**Links**

- `endpoints/get_entity_type_id_field_upload`
- `endpoints/post_links_complete_upload`
- `endpoints/get_entity_type_id_field_upload_multipart`
- `endpoints/post_entity_type_id_field_upload_multipart_abort`
- `findings/044_multipart_upload`