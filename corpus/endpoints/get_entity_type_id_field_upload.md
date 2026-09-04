---
endpoint: GET /entity/<type>/<id>/<field>/_upload
coverage: measured
tags: [upload, media, image, async]
scope: api
measured: sandbox project written
verdict: Step one of three. `filename` is a required query parameter and its absence is 400 `filename is missing`; the reply holds `links.upload` and a `links.complete_upload` already prefixed with `/api/v1`.
---

# GET /entity/<type>/<id>/<field>/_upload

**Params**

| part | value |
|---|---|
| `<field>` | the media field, `image`, `sg_uploaded_movie` |
| `filename` | **required** query parameter. Its extension decides the upload type |

**Sample requests**

```python
r = c.get("/entity/shots/7652/image/_upload", params={"filename": "probe041.png"})
info, links = r.json()["data"], r.json()["links"]
```

```json
{
  "data": {
    "timestamp": "2026-09-04T03:53:31Z",
    "upload_type": "Thumbnail",
    "upload_id": null,
    "storage_service": "s3",
    "original_filename": "probe041.png",
    "multipart_upload": false
  },
  "links": {
    "upload": "<media-url>",
    "complete_upload": "/api/v1/entity/shots/7652/image/_upload"
  }
}
```

Without `filename`:

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
             "source": {"filename": ["filename is missing"]}}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | links minted |
| 400 | `source: {"filename": ["filename is missing"]}` |
| 404 | `Field 'Shot.attachments' does not exist.` when the type has no such field |

**Edge cases**

- `links.complete_upload` is the **same path** as this call, differing only by method, and it comes back
  with `/api/v1` already on it. A client that prefixes it again gets 404 with `source: null`, which reads
  as "this is not a valid upload target" rather than "your URL is wrong".
- `upload_type` is derived from the field and the filename: `Thumbnail` for `image`, `Attachment` for
  the fieldless form. Nothing in the request names it.
- `data` is the `upload_info` that step three needs. Keep the whole object rather than picking keys out
  of it.

**Links**

- `endpoints/put_links_upload`
- `endpoints/post_links_complete_upload`
- `endpoints/get_entity_type_id_upload`
- `field_types/image`
- `findings/013_upload_media`