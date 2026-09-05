---
evidence: [findings/039_upload_silent_failures, findings/013_upload_media]
endpoints: [POST <links.complete_upload>]
kind: api
status: unreported
scope: api
confirmed: 2026-09-04
measured: sandbox project, one Note and two Attachments, all deleted
summary: POST links.complete_upload answers 201 and creates an Attachment when the presigned PUT never happened, and nothing on the row separates it from a good upload.
---

# 002_complete_upload_without_bytes

**Expected** Completing an upload whose bytes were never PUT is rejected, or the Attachment it creates
is distinguishable from one whose file is present.

**Actual** Two runs, identical but for the PUT:

| | no PUT | bytes PUT |
|---|---|---|
| `complete_upload` status | `201` | `201` |
| Attachment row created | yes | yes |
| `filename` | `report.csv` | `report.csv` |
| `file_size` | `null` | `null` |
| `GET` the stored file | `404` | `200` |
| bytes downloaded | none | 30 |

`file_size` is `null` on a good upload as well, so it separates nothing. Fetching the stored file is the
only test, and it costs a round trip per Attachment.

The response body compounds it:

```
POST <links.complete_upload> -> 201
content-type: application/json; charset=utf-8
body: ' '   (1 character)
```

One space, declared as JSON. A client calling `.json()` raises after the write has already landed, and
the body never names the row, so the id has to be recovered by diffing the parent's attachments.

**Reproduce**

```
curl -sS "$SITE/api/v1/entity/notes/<id>/attachments/_upload?filename=report.csv" \
  -H "Authorization: Bearer $TOKEN"
# 200. Keep the data block

# Skip the PUT to links.upload entirely, then:
curl -sS -i -X POST "$SITE/api/v1/entity/notes/<id>/attachments/_upload" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"upload_info": <the data block, verbatim>, "upload_data": {}}'
# 201, content-type application/json, body is a single space

# The Attachment is on the Note, and its file is not there
curl -sS -o /dev/null -w '%{http_code}\n' "<this_file.url of the new Attachment>"
# 404
```

**Impact** A media pipeline whose PUT fails on one file in a thousand produces an Attachment row that
looks correct on the record and resolves to nothing. Neither the status code, the row, nor `file_size`
says so, so the breakage is found by a person opening the file, at whatever remove from the run that
made it. Verifying at write time costs an extra fetch per upload.

**Proposed change** Have `complete_upload` check the object before it creates the row, and answer 4xx
when the bytes are absent. Failing that, record the object's size on the Attachment so `file_size`
separates the two cases. Independently: return a JSON body naming the created row, or answer `204` with
no body, rather than a single space under `content-type: application/json`.
