---
tags: [media, attachment, upload, error-handling, trap, note, silent]
endpoints: [GET /entity/<type>/<id>/_upload, PUT <links.upload>, POST <links.complete_upload>]
phase: upload
scope: api
measured: sandbox project written, one Note and two Attachments, all deleted
verdict: complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.
---

# 039_upload_silent_failures

**Q** Which steps of the three-call upload can fail without saying so?

**Endpoint** `GET /entity/notes/{id}/attachments/_upload -> PUT S3 -> POST links.complete_upload`

**Docs claim** The upload is a multi-step presigned flow. Nothing states what happens when a step is
skipped, or what `complete_upload` returns.

**Actual**

One step is loud. `filename` is required on step one, and omitting it is a 400 that names it:

```
GET /entity/notes/<id>/attachments/_upload -> 400
{"filename": ["filename is missing"]}
```

Everything after that is quiet.

**The link is already prefixed**

`links.complete_upload` comes back absolute against the site, with `/api/v1` already on it:

```
/api/v1/entity/notes/<id>/attachments/_upload
```

A client holding an API base URL prefixes it again and gets a 404 that names nothing:

```
POST /api/v1/api/v1/entity/notes/<id>/attachments/_upload -> 404
{"status": 404, "code": 103, "title": "Not Found", "source": null, "detail": null}
```

`source` and `detail` are both null, so the error reads as "a Note is not a valid upload target" rather
than "your URL is wrong". Post to `links.complete_upload` unchanged.

**Skipping the PUT**

Send `complete_upload` with valid `upload_info` and never PUT the bytes:

| | no PUT | bytes PUT |
|---|---|---|
| `complete_upload` status | `201` | `201` |
| Attachment row created | yes | yes |
| `filename` | `report.csv` | `report.csv` |
| `file_size` | `null` | `null` |
| GET the stored file | `404` | `200` |
| bytes downloaded | none | 30 |

The row is created either way. `filename` and `file_size` are identical, and `file_size` is `null` on a
good upload as well, so it separates nothing. The only difference is whether the stored file is there.

**What `complete_upload` returns**

```
POST <links.complete_upload> -> 201
content-type: application/json; charset=utf-8
body: ' '   (1 character)
```

A single space, declared as JSON. `response.json()` raises. The response never names the row it created,
so a client that parses it crashes after the write has already landed, orphaning the Attachment.

**Teaches**

| do | why |
|---|---|
| Check the PUT's own status code | it is the only step that proves the bytes reached S3 |
| Post to `links.complete_upload` verbatim | `/api/v1` is already on it, and prefixing again is a 404 with a null `source` |
| Never parse the `complete_upload` body | it is one space, and `.json()` raises after the write landed |
| Read the new id by diffing the parent's attachments before and after | `complete_upload` does not return it |
| Never treat `file_size` as proof of content | it is `null` on a good upload |

To verify an upload actually holds bytes, fetch `this_file.url` and check the status. Nothing on the
Attachment row answers it.
