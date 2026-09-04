---
endpoint: POST /transcode/attachment_metadata/<id>
coverage: measured
tags: [transcode, media, async, silent]
scope: api
measured: sandbox project written, one Version and its uploaded Attachment, both deleted
verdict: Records video metadata for media transcoded outside Flow PT. 200 with a body of one space, and none of the six values reads back on the Attachment; only `updated_at` moves.
---

# POST /transcode/attachment_metadata/<id>

`<id>` is an **Attachment** id, not the id of the entity the media hangs on. The path has no
`/entity` segment and no type.

**Params**

| key | type | meaning |
|---|---|---|
| `width` | integer | pixels |
| `height` | integer | pixels |
| `display_aspect_ratio` | number | |
| `frame_rate` | number | frames per second |
| `nb_frames` | integer | duration in frames |
| `start_frame` | integer | |

Every key is optional. The body is the keys to set.

**Sample requests**

```python
att = c.get("/entity/versions/31850", params={"fields": "sg_uploaded_movie"}
            ).json()["data"]["attributes"]["sg_uploaded_movie"]["id"]
r = c.post(f"/transcode/attachment_metadata/{att}", json={
    "width": 1920, "height": 1080, "display_aspect_ratio": 1.7778,
    "frame_rate": 24.0, "nb_frames": 1440, "start_frame": 7})
print(r.status_code, r.headers["Content-Type"], repr(r.text))
# 200 application/json; charset=utf-8 ' '
```

Reading the Attachment back before and after, the only fields that differ are `updated_at` and the
freshly signed `this_file` URL. `metadata` stays `null`.

A wrong type:

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
  "source": {"width": ["width must be an integer"]}}]}
```

An id no Attachment has, and the id of the Version the media hangs on:

```json
{"error": "Attachment 999999999 not found"}
```

**Response codes**

| status | when |
|---|---|
| 200 | accepted. Body is a single space |
| 200 | an empty body, or keys the schema does not name. Both accepted |
| 400 | `width must be an integer`, and the same shape for each typed key |
| 404 | `{"error": "Attachment <id> not found"}` |

**Edge cases**

- **The 404 is not a JSON:API error.** `{"error": "..."}` is a bare string under `error`, with no
  `errors[]` array, no `status`, no `code` and no `source`. A client reading `body["errors"][0]`
  everywhere else raises `KeyError` here.
- `{}` and `{"nope": 1}` both answer 200. Unknown keys are discarded without a word, so a typo in a
  key name looks like a success.
- Nothing the call sets is readable over REST on the Attachment. `width`, `frame_rate` and the rest
  are not Attachment fields, and the row's own `metadata` field stays `null`.
- Pass the Attachment id. A Version id answers `Attachment <id> not found` with the Version's number
  in it, which reads as a missing row rather than a wrong type.

**Links**

- `endpoints/post_entity_type_id_field_upload`
- `endpoints/post_links_complete_upload`
- `entity_types/Attachment`
- `findings/013_upload_media`
- `findings/044_multipart_upload`