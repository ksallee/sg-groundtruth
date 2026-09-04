---
endpoint: GET /entity/<type>/<id>/<field>/_upload/multipart
coverage: measured
tags: [multipart, etag]
scope: api
measured: sandbox project written, one Version, all multipart uploads aborted, all rows deleted
verdict: Step two of a multipart transfer, once per part after the first. Walk `links.get_next_part` rather than building it: each reply holds the part's presigned `upload` and the link to the part after.
---

# GET /entity/<type>/<id>/<field>/_upload/multipart

`links.get_next_part` appears on the init only when it was called with `multipart_upload=true`. It
comes back root-relative with `/api/v1` already on it and every parameter filled in, pointing at
`part_number=2`. Each call answers with the next link in the chain.

**Params**

| part | value |
|---|---|
| `filename` | required. `filename is missing` when absent |
| `upload_type` | required. `Attachment` or `Thumbnail`, from the init |
| `timestamp` | required. The init's `timestamp`, verbatim |
| `part_number` | required. The part this URL will hold |
| `upload_id` | not listed as missing by the 400, and its absence still fails. See **Edge cases** |

**Sample requests**

```python
info, links = b["data"], b["links"]
etags = []
up, nxt = links["upload"], links["get_next_part"]
for chunk in chunks:                      # 5 MiB each, the last one any size
    etags.append(requests.put(up, data=chunk).headers["ETag"].strip('"'))
    l = c.get(nxt).json()["links"]        # nxt already has /api/v1 on it
    up, nxt = l["upload"], l["get_next_part"]
```

```json
{"links": {
  "upload": "<media-url>",
  "get_next_part": "/api/v1/entity/versions/31850/sg_uploaded_movie/_upload/multipart?filename=plate.mov&part_number=3&timestamp=2026-09-04T04%3A41%3A49Z&upload_id=<152 chars>&upload_type=Attachment"}}
```

No parameters at all:

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
  "source": {"upload_type": ["upload_type is missing"], "filename": ["filename is missing"],
             "timestamp": ["timestamp is missing"], "part_number": ["part_number is missing"]}}]}
```

Every parameter except `upload_id`:

```json
{"errors": [{"id": 1, "status": 400, "code": 103,
  "title": "Could not generate upload url. Check the site settings.",
  "source": {}, "detail": null}]}
```

An `upload_id` that was never minted:

```json
{"links": {"upload": "<media-url>"}}
```

**Response codes**

| status | when |
|---|---|
| 200 | a presigned URL for that part |
| 400 | `source` naming any of `filename`, `upload_type`, `timestamp`, `part_number` |
| 400 | `Could not generate upload url. Check the site settings.` when `upload_id` is absent |
| 404 | the record does not exist |

**Edge cases**

- `upload_id` is required and is the one parameter the validator does not check for. Omitting it
  produces `Could not generate upload url. Check the site settings.`, which points at site
  configuration and not at the missing parameter.
- **The `upload_id` is never validated.** `upload_id=nope` answers 200 with a presigned URL. Bytes
  PUT to it are accepted and the transfer fails only at completion, with
  `Error completing multipart upload.`
- The last reply in a chain still holds a `get_next_part` for a part that will never exist. Stop when
  the file is exhausted, not when the chain ends.
- `part_number=1` answers 200 as well, minting a second URL for the part the init already covered.

**Links**

- `endpoints/get_entity_type_id_field_upload`
- `endpoints/get_entity_type_id_upload_multipart`
- `endpoints/post_entity_type_id_field_upload`
- `endpoints/post_entity_type_id_field_upload_multipart_abort`
- `findings/044_multipart_upload`