---
tags: [image, dotted-field, media, trap]
endpoints: [POST /entity/<type>/_search, GET /entity/<type>/<id>, GET /entity/<type>/<id>/<field>, POST /entity/<type>/_summarize]
phase: read
scope: api
measured: sample project 1 of 1, 300 Shots, their 1500 Tasks and 99 Versions
verdict: entity.Shot.image returns the Shot's thumbnail as a presigned S3 URL under attributes, same object, fresh signature, in the same call. image is_not null matched 50 Shots whose image reads null.
---

# 081_dotted_image

**Q** Does a dotted `entity.Shot.image` return a presigned URL the way `image` does on the Shot itself?

**Endpoint** `POST /entity/tasks/_search ; GET /entity/tasks/<id> ; GET /entity/shots/<id>/image`

**Docs claim** Silent on image through a dotted path.

**Actual**

```
300 Shots; filter image is_not null matches 300, image is null matches 0
  image read on those 300: a signed S3 URL 250, null 50
tasks?fields=entity,entity.Shot.image: 1500 rows on a Shot
  returned under attributes on 1500
  Shot's image a URL (1250 rows): a signed S3 URL on 1250; same path as the Shot's own, different signature
  Shot's image null (250 rows): null on 250
  query keys X-Amz-Algorithm, X-Amz-Credential, X-Amz-Date, X-Amz-Expires, X-Amz-Security-Token,
             X-Amz-Signature, X-Amz-SignedHeaders, response-content-disposition, x-amz-meta-user-id, ...
versions?fields=entity.Shot.image: 99 rows, all on Shots whose image reads null; null on 99
tasks, entity.Shot.image is_not null -> 200 {"id": 1500}; is null -> 200 {"id": 0}
GET /entity/tasks/<id>?fields=entity.Shot.image -> 200, a signed S3 URL
GET /entity/shots/<id>/image -> 200 application/json {"data": "<media-url>", "links": {...}}
```

**Teaches**

- A dotted image column costs nothing extra. It is returned under `attributes` keyed by the dotted name,
  as the same S3 object the Shot's own `image` names, re-signed for this read (`field_types/image`).
  Key a cache on the object path, never on the full URL.
- **`image is_not null` and a null read disagree.** On the probed site 50 Shots match `is_not null` and
  read `null`, and the dotted filter matched all 1500 Tasks while 250 of them read `null`. Filter to
  narrow, then test the value you read.
- `GET /entity/shots/<id>/image` returns the same URL wrapped in `{"data": ...}`, one call per row.
  Prefer the dotted field on the row you already fetch.
