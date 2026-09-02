---
tags: [write, upload, attachment, provenance, version, multi-entity, filter, header]
scope: api
verdict: Leave the field out of the _upload path and the file is stored as an Attachment on attachment_links; read it back with POST /entity/attachments/_search, never flat filter[].
---

# 014_attach_file

**Q** How does an arbitrary file attach to a Version, and how is it read back?

**Endpoint** `GET /entity/versions/{id}/_upload (no field) -> PUT -> POST complete_upload ; POST /entity/attachments/_search`

**Docs claim** Arbitrary files attach to a Version as Attachment entities. Silent on which Content-Type each endpoint wants.

**Actual**

```
1. init (no field in path) -> 200, upload_type=Attachment
2. PUT 73b -> 200
3. complete -> 415 {"errors":[{"id":"75a2b5264f11afa6e6b1b1fcdf7758ef","status":415,"code":103,"title":"Unsupported Content-Type 'application/vnd+shotgun.api3_array+json'","source":{"content_type":"Content-Type must be
   ^ the probe truncates at 200 chars, so the tail of that sentence is <unverified> here; probe 013 completes the same step with application/json and gets 201.

recovered read-only - POST /entity/attachments/_search with the wrong type prints the whole sentence:
{"errors":[{"id":"c9fa7433ec34c190c86ad73a0cff3327","status":415,"code":103,"title":"Unsupported Content-Type 'application/json'","source":{"content_type":"Content-Type must be one of: 'application/vnd+shotgun.api3_array+json', 'application/vnd+shotgun.api3_hash+json'."},"detail":null,"meta":null}]}

Attachment fields (30): attachment_links, attachment_reference_links, cached_display_name, created_at,
  created_by, description, display_name, file_extension, file_size, filename, filmstrip_image, id, image,
  ... image_source_entity, local_storage, original_fname, processing_status, project, this_file, updated_at

flat filter[attachment_links]=Version,{id} -> 400 "API read() invalid/missing entity hash: \"Version\""

POST /entity/attachments/_search  filters [["attachment_links", "is", {"type": "Version", "id": <id>}]]
attachments linked to this Version: 3
  id=1927 name='workflow.json' type=None size=None
    this_file: {"url": "<media-url>
  id=1926 name='workflow.json' type=None size=None
  id=1925 name='render.png'    type=None size=None
```

**Teaches**
- The field in the path picks the upload type: omit it and `upload_type=Attachment`, giving an Attachment entity reachable through `attachment_links`. The three steps are otherwise those of media (probe 013).
- The Content-Type is per endpoint, never per site:

  | endpoint | Content-Type |
  |---|---|
  | `complete_upload` | `application/json`; the vendor type 415s |
  | `_search`, `_summarize` | `application/vnd+shotgun.api3_array+json` or `...api3_hash+json`; `application/json` 415s (probe 004) |

- A multi-entity field cannot be filtered by flat `filter[]` params: 400 `API read() invalid/missing entity hash: "Version"`. It needs a `{type, id}` hash, and only a `_search` body can express one. The same message, with the offending value in place of `"Version"`, answers a bare id inside a `_search` body: `API update() invalid/missing entity hash: 26332` on write, `in [A]` bare int 400 `invalid/missing entity hash: 26342` on filter (field_types/multi_entity). Probe 017 records a different message, `invalid/missing entity hash string 'type'`, returned when the hash is present but has no `type` key.
- This run's step 3 failed, so it created nothing. On the probed site the three attachments listed are from earlier runs, and this finding does not itself verify that a completed upload appears in that list.
