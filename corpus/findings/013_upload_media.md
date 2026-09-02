---
tags: [write, upload, media, attachment, version, async]
scope: api
verdict: Media upload is three calls: GET {field}/_upload for the presigned links, PUT the bytes to links.upload, POST links.complete_upload with upload_info and upload_data.
---

# 013_upload_media

**Q** What is the full media upload round trip on a Version, start to finish?

**Endpoint** `GET /entity/versions/{id}/{field}/_upload -> PUT S3 -> POST complete_upload`

**Docs claim** Media upload is a multi-step presigned flow.

**Actual**

```
=== thumbnail via /image/_upload
  1. init 200 — data keys: ['multipart_upload', 'original_filename', 'storage_service', 'timestamp', 'upload_id', 'upload_type']
     link keys: ['complete_upload', 'upload']
     upload_type=Thumbnail storage=s3 multipart=False
  2. PUT to presigned S3 -> 200 (etag "9cfd8018bfbd3962b3b39764af098b2e")
  3. POST /api/v1/entity/versions/26263/image/_upload -> 201

=== media field via /sg_uploaded_movie/_upload
  1. init 200 — data keys: ['multipart_upload', 'original_filename', 'storage_service', 'timestamp', 'upload_id', 'upload_type']
     link keys: ['complete_upload', 'upload']
     upload_type=Attachment storage=s3 multipart=False
  2. PUT to presigned S3 -> 200 (etag "9cfd8018bfbd3962b3b39764af098b2e")
  3. POST /api/v1/entity/versions/26263/sg_uploaded_movie/_upload -> 201

=== read back, immediately after the 201
  attributes: {"code": "sh010_v002", "image": "<FPT_API_SITE_URL>/images/status/transient/thumbnail_pending.png", "sg_uploaded_movie": {"url": "<media-url>
  relationships: []
```

**Teaches**
- Step 3 takes `{"upload_info": <the data block from step 1, verbatim>, "upload_data": {}}` and answers 201. `upload_data` must be present even though it is an empty dict; omitting it is reported to 400 with `upload_data is missing`, but this probe always sends it, so that error body is `<unverified>` here.
- The field in the path sets `upload_type`:

  | field in the `_upload` path | `upload_type` |
  |---|---|
  | `image` | `Thumbnail` |
  | any other field | `Attachment` |
  | no field at all | `Attachment` (probe 014) |

- Transcoding is async. Reading the field straight back returns a placeholder under `/images/status/transient/`, so a client must test for that path prefix rather than treat the value as media. Once transcoded, `image` is a plain presigned URL and `sg_uploaded_movie` a dict with `url` (probe 021).
