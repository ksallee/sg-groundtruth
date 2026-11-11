---
tags: [cors, browser, upload, etag, multipart, header]
endpoints: [GET /entity/<type>/<id>/<field>/_upload, PUT <links.upload>, POST <links.complete_upload>, POST /entity/<type>/<id>/<field>/_upload/multipart_abort, GET /entity/<type>/<id>/<field>]
phase: upload
scope: api
measured: sandbox project written, 2026-11-11; two Versions and their Attachments deleted; one multipart init aborted
coverage: partial
unmeasured: a real browser run, and a size cap: the largest single PUT sent was 7.6 MB (probe 123). Blocked on the work
verdict: The presigned upload host answers any Origin with `*`, allows PUT with content-type and exposes `ETag`, so a page can upload, multipart included. A URL is refused after 900 s.
---

# 125_upload_host_cors

**Q** Can a browser page PUT to the presigned upload host, read the part ETag, and read the stored
file back, and how long is a presigned URL good for?

**Endpoint** `GET /entity/<type>/<id>/<field>/_upload ; PUT <links.upload> ; GET <stored file url>`

**Docs claim** Silent on browsers and on how long an upload URL lives.

**Actual**

```
links.upload host <bucket>.s3-accelerate.amazonaws.com, https
  query X-Amz-Algorithm AWS4-HMAC-SHA256, X-Amz-Expires 900, X-Amz-SignedHeaders host,
        X-Amz-Credential, X-Amz-Date, X-Amz-Security-Token, X-Amz-Signature

OPTIONS <links.upload>  Origin https://example.invalid | http://localhost:5173 | null
                        Access-Control-Request-Method PUT, -Headers content-type     -> 200
  access-control-allow-origin: *
  access-control-allow-methods: GET, HEAD, PUT
  access-control-allow-headers: content-type          (echoes x-amz-meta-probe when asked)
  access-control-expose-headers: ETag
  access-control-max-age: 0
  vary: Origin, Access-Control-Request-Headers, Access-Control-Request-Method
  no access-control-allow-credentials

PUT <links.upload>  Origin, Content-Type image/jpeg  -> 200, the same CORS headers, etag present
GET <sg_uploaded_movie.url>  Origin                  -> 200 direct, no redirect, bytes identical,
                                                        the same CORS headers
multipart part URL (probe 044): OPTIONS 200 and PUT 200, same headers, ETag exposed
OPTIONS <site>/api/v1/.../sg_uploaded_movie/_upload  -> 200, origin echoed (probe 062)

two upload URLs minted together: PUT at 840 s -> 200; PUT at 910 s -> 403
  <Code>AccessDenied</Code><Message>Request has expired</Message><X-Amz-Expires>900</X-Amz-Expires>
```

**What a page on another origin can do**

| step | host | from a page |
|---|---|---|
| `GET .../_upload` | the site, `/api/v1` | yes, with `Authorization` (probe 062) |
| `PUT <links.upload>` | presigned S3 | yes. `fetch` without `credentials`; `*` refuses a credentialed request |
| read `ETag` off a part PUT | presigned S3 | yes, it is in `access-control-expose-headers` |
| `POST <links.complete_upload>` | the site | yes |
| `GET` the stored file | presigned S3 | yes, readable bytes, so a canvas drawn from it is not tainted |

**Lifetime**: 900 s from the `_upload` call, as `X-Amz-Expires` says. A PUT at 840 s succeeded and
one at 910 s was refused with 403 `Request has expired`, an S3 XML body rather than `errors[]`.

**Teaches**
- A browser can run the whole upload, multipart included: the ETag that probe 044's completion needs
  is exposed. Probe 062's caveat that a page cannot read `ETag` holds for `/api/v1`, not this host.
- Fetch the upload URL when the bytes are ready to go, not when the photo is taken: it is signed for
  15 minutes. Ask for a fresh `_upload` per attempt; a part chain's `get_next_part` mints the next.
- Send the PUT with `credentials: "omit"` (the `fetch` default for cross-origin is `same-origin`,
  which also omits). `max-age: 0` means every PUT is preflighted.
- Evidence is response headers read by a process, which no CORS rule blocks. A browser applying the
  standard algorithm to these headers allows the calls above; no browser was run.
