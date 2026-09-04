---
endpoint: PUT /entity/<type>/<id>/<field>/_upload
tags: [storage, media]
scope: api
measured: sandbox project written, one Version, deleted
verdict: The `storage_service: "sg"` upload target, on the Flow PT host. A site on `s3` returns an S3 `links.upload` instead, and calling this route directly is 400 for four missing signature parameters.
---

# PUT /entity/<type>/<id>/<field>/_upload

The init's `links.upload` and this path are the same route when `storage_service` is `sg`: the bytes
go to the Flow PT application server rather than to S3. The signature and the identity of the
uploader are query parameters the init put on the link, so the route is unusable without a link the
init minted.

**Params**

| part | value |
|---|---|
| URL | `links.upload` from the init, verbatim, when `storage_service` is `sg` |
| `filename` | required |
| `signature` | required. Minted by the init |
| `user_id`, `user_type` | required. The uploading account. A script key authenticates as `ApiUser` |
| `expiration` | required. Unix timestamp |
| body | the raw bytes |
| `Authorization` | not part of the signature. `endpoints/put_links_upload` covers the header rule |

**Sample requests**

On the probed site `storage_service` is `s3`, so no `links.upload` points here. Calling the path
directly with only `filename`:

```python
c.put("/entity/versions/31850/sg_uploaded_movie/_upload",
      params={"filename": "plate.mov"}, data=b"...")
```

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
  "source": {"user_id": ["user_id is missing"], "user_type": ["user_type is missing"],
             "expiration": ["expiration is missing"], "signature": ["signature is missing"]}}]}
```

The init that would have produced a link here:

```json
{"timestamp": "2026-09-04T04:41:49Z", "upload_type": "Attachment", "upload_id": null,
 "storage_service": "s3", "original_filename": "plate.mov", "multipart_upload": false}
```

**Response codes**

| status | when |
|---|---|
| 200 | stored, with `data.upload_id` and `links.complete_upload` in the reply |
| 400 | `source` naming `signature`, `user_id`, `user_type` and `expiration` as missing |
| 404 | the record does not exist |

**Edge cases**

- **Read `storage_service` before assuming which host holds the bytes.** `s3` puts `links.upload` on
  Amazon and this route is never called; `sg` puts it here. A client that hardcodes either one breaks
  on the other kind of site.
- Where the single-PUT S3 target answers 200 with an empty body and an `ETag`, this route is declared
  to answer 200 with `data.upload_id` and `links.complete_upload`. Unmeasured: no `sg` site was
  available.
- The four missing parameters are the whole signature. Never construct this URL; use the one the init
  returned.

**Links**

- `endpoints/get_entity_type_id_field_upload`
- `endpoints/put_links_upload`
- `endpoints/put_entity_type_id_upload`
- `endpoints/post_entity_type_id_field_upload`
- `findings/044_multipart_upload`