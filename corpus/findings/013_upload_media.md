---
tags: [write, upload, media, attachment, version, async]
verdict: Three steps, no shortcuts. 1) GET /entity/versions/{id}/{field}/_upload?filename=X returns links.upload (presigned S3) and links.complete_upload. 2) PUT the raw bytes to links.upload. 3) POST links.complete_upload with {'upload_info': <the data block from step 1 verbatim>, 'upload_data': {}} -> 201. Omitting upload_data 400s with 'upload_data is missing' even though it is empty. Field choice sets upload_type: /image/ is a Thumbnail, any other field is an Attachment. Transcoding is ASYNC - reading the field straight back returns a placeholder under /images/status/transient/, so detect that path prefix rather than treating it as the real media.
---

# 013_upload_media

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

=== read back
  attributes: {"code": "obsidian_v002", "image": "<FPT_API_SITE_URL>/images/status/transient/thumbnail_pending.png", "sg_uploaded_movie": {"url": "<media-url>
  relationships: []
```

**Verdict** Three steps, no shortcuts. 1) GET /entity/versions/{id}/{field}/_upload?filename=X returns links.upload (presigned S3) and links.complete_upload. 2) PUT the raw bytes to links.upload. 3) POST links.complete_upload with {'upload_info': <the data block from step 1 verbatim>, 'upload_data': {}} -> 201. Omitting upload_data 400s with 'upload_data is missing' even though it is empty. Field choice sets upload_type: /image/ is a Thumbnail, any other field is an Attachment. Transcoding is ASYNC - reading the field straight back returns a placeholder under /images/status/transient/, so detect that path prefix rather than treating it as the real media.
