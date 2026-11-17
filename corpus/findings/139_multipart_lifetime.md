---
tags: [multipart, upload, storage, trap]
endpoints: [GET /entity/<type>/<id>/_upload, GET /entity/<type>/<id>/_upload/multipart, PUT <links.upload>, POST <links.complete_upload>, POST /entity/<type>/<id>/_upload/multipart_abort]
phase: upload
scope: api
measured: sandbox project written, 2026-11-11 (twice); one Note, three multipart uploads, two Attachments deleted
coverage: partial
unmeasured: an upload_id older than 1230 s. Blocked on time: `139 --write --wait <seconds>` measures any age
verdict: An upload_id still completed 1230 s after its init, with part 2 minted then. The link's `timestamp` is not age-checked: it is part of the stored key, so another value signs a URL S3 answers 404.
---

# 139_multipart_lifetime

**Q** How long does a multipart `upload_id` live, is the `timestamp` in a part link checked for age, and
does a part URL minted 20 minutes after the init still complete?

**Endpoint** `GET /entity/<type>/<id>/_upload?multipart_upload=true ; GET .../_upload/multipart ; PUT <links.upload> ; POST <links.complete_upload>`

**Docs claim** Silent on lifetimes. Probe 044 measured the flow in one sitting, probe 125 a presigned
URL refused after 900 s.

**Actual**

```
M1 init t0, timestamp 2026-11-11T19:07:29Z; get_next_part query: filename part_number timestamp upload_id upload_type
  part 1 (5 MiB) PUT at t0+3s                  -> 200, ETag
  part 1 URL PUT again at t0+1230s             -> 403 AccessDenied "Request has expired", X-Amz-Expires 900
  get_next_part at t0+1231s                    -> 200, a fresh part 2 URL
  part 2 PUT                                   -> 200
  complete with both ETags at t0+1232s         -> 201; the stored file reads back

M2 part 1 URL minted by GET .../_upload/multipart, the init's query with timestamp replaced
  2020-01-01T00:00:00Z  -> 200; URL path differs from the init's; X-Amz-Date the call's own time
                           PUT -> 404 <Code>NoSuchUpload</Code> "The specified upload does not exist.
                                  The upload ID may be invalid, or the upload may have been aborted or completed."
  zz                    -> 400 {"status": "error", "error": "no time information in \"zz UTC\""}
  omitted               -> 400 code 103 "Request Parameters invalid." source {"timestamp": ["timestamp is missing"]}
  the init's own value  -> 200; same path as the init's URL; PUT 200; complete 201
```

**Teaches**
- A resumed upload keeps its `upload_id`, `timestamp` and the ETags of finished parts, and asks
  `get_next_part` for a fresh URL per part: every URL dies 900 s after it was minted (probe 125), the
  `upload_id` did not within 1230 s. Persist the init's whole `data` object with the ETags.
- `timestamp` is an identifier, not a freshness check. A wrong value is accepted at minting and fails
  only at the part `PUT`, as an S3 404 that blames the upload ID. Send the init's value verbatim.
- A garbage `timestamp` answers a bare `{"status": "error", ...}` body outside the `errors[]`
  envelope; parse both shapes on this call.
- An init that is never completed nor aborted stays open on storage (probe 044). Its lifetime there
  is the storage's and was not measured past 1230 s.
