---
tags: [upload, storage, cost]
endpoints: [GET /entity/<type>/<id>/_upload, PUT <links.upload>, POST <links.complete_upload>, GET /entity/<type>/<id>/<field>]
phase: upload
scope: api
measured: sandbox project written, 2026-11-11 (twice); one Note, three Attachments of 50, 200 and 1000 MB, each deleted at once
coverage: partial
unmeasured: sizes above 1000 MB, stopped there by design. S3 documents five gigabytes as one PUT's ceiling
verdict: One presigned PUT took 1000 MB at 200 and the stored object read back at exactly 1000000000 bytes. No refusal up to there; at about 8 MB/s a 1000 MB PUT took two minutes.
---

# 140_presigned_put_size

**Q** What is the largest single presigned `PUT` the upload host accepts, and how long does it take?

**Endpoint** `GET /entity/<type>/<id>/_upload ; PUT <links.upload> ; POST <links.complete_upload>`

**Docs claim** Silent on a size limit. Probe 044 found nothing in the API refuses a single-PUT upload
for its size.

**Actual**

```
field-less upload to one Note, zero bytes from a sparse file, one size at a time
size      PUT    time     rate        complete  stored object, GET Range bytes=-1
50 MB     200    6.5 s    7.6 MB/s    201       206 Content-Range bytes 49999999-49999999/50000000
200 MB    200    20.1 s   10.0 MB/s   201       206 .../200000000
1000 MB   200    116.2 s  8.6 MB/s    201       206 .../1000000000
second run: 9.3 s, 26.9 s, 119.4 s

Attachment.file_size: null after every completion (probe 039)
HEAD on this_file.url -> 403 (the URL is signed for GET; probe 141)
```

**Teaches**
- Size is not what forces multipart, up to 1000 MB at least. Choose multipart for resumability: a single
  PUT that dies at 90 % starts over, and a 1000 MB PUT here ran two minutes on one connection.
- The upload URL lives 900 s from `_upload` (probe 125). Whether a PUT that starts inside the window
  and ends after it is accepted was not measured. Mint the URL right before the PUT, and keep a
  single PUT small enough to finish inside 900 s at the connection's rate.
- Confirm a stored size with `GET` and `Range: bytes=-1`: `Content-Range` gives the total.
  `file_size` stays null and `HEAD` is refused.
