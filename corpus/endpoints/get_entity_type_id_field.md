---
endpoint: GET /entity/<type>/<id>/<field>
coverage: measured
tags: [attachment, media, image, trap]
scope: api
measured: sample project 1 of 1, read only
verdict: Reads one image or attachment field, and with `?alt` redirects to the bytes. Every other data type is a 400, so this is not a cheap single-field read.
---

# GET /entity/<type>/<id>/<field>

**Params**

| part | value |
|---|---|
| `<field>` | an `image` or `url` field. Anything else is a 400 |
| `?alt` | `original` or `thumbnail`. Redirects to the stored file instead of describing it |
| `Range` | forwarded to storage, and only with `?alt` |

**Sample requests**

```python
ID = 17055
c.get(f"/entity/versions/{ID}/sg_uploaded_movie").json()
```

```json
{"data": {"url": "<presigned URL>", "name": "charA.jpg", "content_type": "image/jpeg",
          "link_type": "upload", "type": "Attachment", "id": 1430},
 "links": {"self": "/api/v1/entity/versions/17055/sg_uploaded_movie"}}
```

An `image` field answers the URL as a bare string:

```json
{"data": "<presigned URL>", "links": {"self": "/api/v1/entity/versions/17055/image"}}
```

Any other field:

```json
{"errors": [{"status": 400, "code": 103,
             "title": "Field Version.code is not an image or attachment.",
             "source": null, "detail": null}]}
```

The bytes, rather than the field:

```python
r = c.get(f"/entity/versions/{ID}/image", params={"alt": "thumbnail"})
r.status_code, r.headers["Content-Type"], len(r.content)   # 200 'image/jpeg' 51730, after a 302

r = c.get(f"/entity/versions/{ID}/image", params={"alt": "original"},
          headers={"Range": "bytes=0-100"})
r.status_code, r.headers["Content-Range"]                  # 206 'bytes 0-100/196291'
```

**Response codes**

| status | when |
|---|---|
| 200 | the field hash, or the file when a redirect was followed |
| 206 | `Range` sent with `?alt` |
| 302 | `?alt` given, `Location` is the presigned storage URL |
| 400 | `Field Version.code is not an image or attachment.` |
| 400 | `source: {"alt": ["alt must be one of: original, thumbnail"]}` |
| 404 | `Field 'Version.sg_not_a_field' does not exist.`, code 103 |
| 404 | `Field sg_uploaded_movie is empty.`, code 104, for `?alt` on an empty `url` field |
| 404 | `File not found`, code 104, for `?alt` on an empty `image` field |
| 406 | a dotted path, with a one-byte `text/html` body |

**Edge cases**

| `<field>` | result |
|---|---|
| `image`, an `image` field | 200, `data` is a URL string |
| `sg_uploaded_movie`, a `url` field | 200, `data` is the attachment hash |
| `code`, `sg_status_list`, `id` | 400 `is not an image or attachment` |
| `entity`, `playlists` | 400, the same message. Use `relationships/<field>` |
| `entity.Shot.code` | 406, one byte |
| a name the type does not have | 404, code 103 |

- A dotted path 406s because the segment after the last dot is read as a format extension, not as a
  field. There is no single-field read for a dotted path.
- `Range` without `?alt` is ignored and the field hash comes back at 200. The header only reaches
  storage once the redirect is in play.
- Reading `image` here costs about the same as `GET /entity/<type>/<id>?fields=image`, because the
  presigned URL is most of both bodies.
- An empty field answers 200 with `"data": null`. Add `?alt` to the same call and it is a 404, worded
  differently per data type: `Field sg_uploaded_movie is empty.` for `url`, `File not found` for
  `image`. Read the field first if the difference between empty and missing matters.

**Links**

- `endpoints/get_entity_type_id`
- `endpoints/get_entity_type_id_field_upload`
- `endpoints/get_entity_type_id_relationships_field`
- `field_types/url`
- `field_types/image`
