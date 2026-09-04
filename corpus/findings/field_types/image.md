---
tags: [media, upload, async, destructive, image]
scope: api
measured: first sample project, 100 Versions; rows written in the sandbox project
summary: A thumbnail for the row, set by uploading a file.
verdict: Only the upload dance sets an image: every value but null 400s, and clearing it also clears `filmstrip_image`. The value is a presigned URL re-signed per read, so store the row id, never the string.
---

# image

**Data type** `image`, probed on `Version.image` and `Version.filmstrip_image` (stock, editable).
`image_blur_hash` is a `text` field, not this type. On the probed site, across all 114 entity types:

| image fields on the type | types |
|---|---|
| `image` and `filmstrip_image` | 39, Version, Shot, Asset, Project and HumanUser among them |
| `image` alone | 10: ClientUser, Department, Episode, Level, PipelineConfiguration, PublishedFileType, Reel, RvLicense, Software, SourceClip |
| neither | 65 |

No type held an `image` field under a third name, and every one found reads `editable: true`.

**Read** A plain string under `attributes`, or `null`. Never under `relationships`. The value is the
only state marker; test for the `/images/status/transient/` prefix, never for truthiness.

| value | state |
|---|---|
| `null` | never uploaded |
| `<site>/images/status/transient/thumbnail_pending.png` | still transcoding |
| any other string | ready |

```
image / filmstrip_image, 100 Versions on the sample project: {null: 99, url str: 1} each
the value: a presigned S3 URL, 1342-1396 chars
  path   /<40 hex chars>/…        a content hash — the stable half
  query  ['X-Amz-Algorithm', 'X-Amz-Credential', 'X-Amz-Date', 'X-Amz-Expires', 'X-Amz-Signature',
          'X-Amz-Security-Token', 'X-Amz-SignedHeaders', 'response-content-disposition',
          'x-amz-meta-user-id', 'x-amz-meta-user-type']
  X-Amz-Algorithm = AWS4-HMAC-SHA256
```

| read | equal to the previous read? | fetch |
|---|---|---|
| `GET /entity/versions/{id}?fields=image` | n/a | `GET` 200 `image/jpeg` 51730 bytes |
| the same `GET` one second later | no, first differing character at index 353 of 1396 | n/a |
| `POST /entity/versions/_search` | no | n/a |
| any of them with `HEAD` | n/a | 403 `application/xml` |
| a string held 706 seconds past its `X-Amz-Expires` | n/a | 403 `<Code>AccessDenied</Code>` |

Re-signed on every read, and the lifetime is `X-Amz-Expires` seconds from `X-Amz-Date`: six reads 20
seconds apart each got a fresh 900, one read got 646, so take the number from the URL. Cache the
entity id and re-read, never the string. Fetch with `GET`; the signature covers no other method.

**Write** Not assignable, on create or on update. `null` is the only value the field accepts.

| sent | code | result |
|---|---|---|
| `"https://example.com/thumb.png"` | 400 | the `expected [Hash, … NilClass]` body below |
| `"data:image/png;base64,iVBORw0…"` (154 chars) | 400 | same, `… but got String: "data:image/png;base64,…"` |
| `"/images/status/transient/x.png"` | 400 | same |
| `""` | 400 | same, `… but got String: ""` |
| `{"url": "https://example.com/thumb.png"}` | 400 | `invalid/missing entity hash string 'type'` |
| `{}` | 400 | same |
| `{"type": "Attachment", "id": 0}` | 400 | `Write access of the 'image' data type … not yet supported` |
| `{"type": "Attachment", "id": <a real Attachment>}` | 400 | the same message; an id that resolves changes nothing |
| `null` | 200 | cleared |
| the same string in a `POST /entity/versions` body | 400 | `API create() Version.image expected [Hash, …` |

```
API update() Version.image expected [Hash, ActiveSupport::HashWithIndifferentAccess, ActionDispatch::Http::Parameters, ActionDispatch::Http::ParamsHashWithIndifferentAccess, NilClass] data type(s) but got String: "https://example.com/thumb.png"
API update() invalid/missing entity hash string 'type': {"url" => "https://example.com/thumb.png"}
 Valid entity types: ["ActionMenuItem", "ApiUser", … 114 of them …, "WorkDayRule"]
API update(): Write access of the 'image' data type (Version.image) not yet supported in API
```

`editable: true` in the schema is wrong; the write fails loudly rather than being taken and discarded
like `cached_display_name` (probe 004). The upload dance is the only way in (probe 013).
`filmstrip_image` takes the same three calls, and the field in the path decides the kind, so both
report `upload_type=Thumbnail`:

```
GET  /entity/versions/{id}/image/_upload?filename=zzprobe.png       -> 200 upload_type=Thumbnail
PUT  {links.upload}  97 bytes                                       -> 200
POST {links.complete_upload} {"upload_info": …, "upload_data": {}}  -> 201
GET  /entity/versions/{id}/filmstrip_image/_upload                  -> 200 upload_type=Thumbnail
```

**Clear**

| sent | code | `image` after | `filmstrip_image` after |
|---|---|---|---|
| `PUT {"image": null}` | 200 | `null` | `null`, cleared with it |
| `PUT {"filmstrip_image": null}` | 200 | unchanged | `null` |
| `PUT {"image": ""}` | 400 | unchanged | unchanged |
| `DELETE /entity/versions/{id}/image` | 404 `Not Found` | unchanged | unchanged |

**Filter** Two relations, and nil is the only legal value:

```
["image", "definitely_not_an_operator", null] -> 400
 title:  "API read() Version.image's 'image' data type doesn't support
          'definitely_not_an_operator' 'relation'"
 source: {"Version.image": " data type doesn't support … Valid relations: ["is", "is_not"]"}
```

| operator | value | matches | code |
|---|---|---|---|
| `is` | `null` | 99 of 100 Versions, no thumbnail | 200 |
| `is_not` | `null` | 1 of 100, has one, transcoded or not | 200 |
| `is` | `""` | `'is' 'relation' expects a nil value for 'image' data type: [""]` | 400 |
| `is` | `"https://x/y.png"` | same, `… data type: ["https://x/y.png"]` | 400 |
| `contains` | `"thumb"` | `doesn't support 'contains'` … `["is", "is_not"]` | 400 |
| `in` | `[null]` | `doesn't support 'in'` … `["is", "is_not"]` | 400 |

`_summarize` grouping on `image` is 400 `Grouping is not allowed for field Version.image.`

| on the same Version | `image` | `url` (`sg_uploaded_movie`) |
|---|---|---|
| read shape | string | dict (probe 021) |
| filter | `is`, `is_not`, nil only | no relation at all (probe 021) |
| transcode state | the path prefix | `sg_uploaded_movie_transcoding_status` (probe 022) |

**Traps**
- `is_not None` matches a row that is still transcoding, so a job that filters and then downloads
  fetches `thumbnail_pending.png`. Filter, then check the prefix on each row.
- Transcoding took ~38 seconds for a 16x16 97-byte PNG. Poll the field every 5 seconds.
- The REST upload never fills `image_blur_hash`: still `null` 102 seconds after the thumbnail settled
  and after a second upload to `filmstrip_image`. The one sample-project row holding one
  (`'YXFZJ]4U-=ISt8oh…'`, 68 chars) was made outside REST. Do not wait on it.
