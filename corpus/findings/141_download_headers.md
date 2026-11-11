---
tags: [browser, cors, header, attachment, media]
endpoints: [GET /entity/<type>/<id>/<field>, GET /entity/<type>/<id>/_upload, PUT <links.upload>, POST <links.complete_upload>]
phase: upload
scope: api
measured: sandbox project written, 2026-11-11; one Note and one 20 MB Attachment, deleted
verdict: A stored file's GET sends Content-Length and Accept-Ranges, answers `*` to any Origin and allows a Range preflight, so a page can show progress, resume with Range and abort. `HEAD` is 403.
---

# 141_download_headers

**Q** Does the stored file's GET (an Attachment's `this_file.url`) send `Content-Length`, can a page read
it and the body under CORS, does it honour `Range`, and can the body be cancelled after the headers?

**Endpoint** `GET <this_file.url> ; GET /entity/<type>/<id>/<field>`

**Docs claim** Silent. Probe 125 read a stored file once and found `access-control-allow-origin: *`.

**Actual**

```
this_file.url: <bucket>.s3-accelerate.amazonaws.com, X-Amz-Expires 900; answered through CloudFront

GET, Origin https://example.invalid                   -> 200, 20000000 b in 1.4 s, bytes identical
  content-length: 20000000        accept-ranges: bytes      content-type: binary/octet-stream
  content-disposition: filename="zzprobe_141.jpg"
  access-control-allow-origin: *  access-control-allow-methods: GET, HEAD, PUT
  access-control-expose-headers: ETag                       access-control-max-age: 0
HEAD on the same URL                                  -> 403, content-type application/xml
OPTIONS, ACRM GET, ACRH range                         -> 200, access-control-allow-headers: range
GET, Range bytes=0-1023                               -> 206, 1024 b, the first KiB
  content-range: bytes 0-1023/20000000
streamed: headers after 0.15 s; 64 KiB read, connection closed at 0.16 s
  the same URL straight after, Range bytes=-16        -> 206, 16 b

GET /api/v1/entity/attachments/<id>/this_file         -> 200 JSON: content_type, id, link_type, name, type, url
```

**What a page on another origin can do**

| need | header | readable by script |
|---|---|---|
| total size, for progress | `Content-Length` | yes: CORS-safelisted, and the response is `*` |
| resume a download | `Range` request, `206`, `Content-Range` | the request yes (preflight allows `range`); `Content-Range` is not exposed, use `Content-Length` of the 206 and the offset sent |
| abort | `AbortController` on the `fetch` | nothing server-side to call |
| the file's MIME type | `Content-Type` | yes; it is what the upload `PUT` sent, here none, so `binary/octet-stream` |

**Teaches**
- Show progress from `Content-Length`: it is sent on the 200, and a script may read it under `*`.
- `HEAD` is refused because the URL is signed for `GET`. Read size with `GET` and `Range: bytes=-1`
  (probe 140), or from the 200's headers before reading the body.
- Abandoning a body is a client-side close; the URL stays usable for a new request until it expires
  900 s after it was read from the API. What S3 bills for a closed transfer was not measured.
- The stored `Content-Type` is S3's default `binary/octet-stream` when the upload `PUT` sends none,
  as this one did; the `.jpg` name does not set it. `Content-Type` is not a signed header
  (probe 125), so a `PUT` may send one; whether the download then answers with it was not measured.
- Evidence is headers read by a process. A browser applying the CORS rules to them allows the above;
  no browser was run.
