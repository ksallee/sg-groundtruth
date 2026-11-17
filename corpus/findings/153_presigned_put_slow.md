---
tags: [upload, storage, browser]
endpoints: [GET /entity/<type>/<id>/_upload, PUT <links.upload>, POST <links.complete_upload>]
phase: upload
scope: api
measured: sandbox project written, 2026-11-17, three runs; one Note per run, its Attachment deleted
coverage: partial
unmeasured: a PUT started between 4 s and 600 s, and a real upload at Wi-Fi speed. Blocked on time: each run takes 17 minutes
verdict: A presigned PUT started at once and ending at 965 s was stored, 3 runs of 3. Every PUT started at 600 s or later and ending past 900 s was 403 `Request has expired`, whatever it sent first.
---

# 153_presigned_put_slow

**Q** Is a presigned PUT that starts inside the URL's 900 s and ends after it accepted?

**Endpoint** `GET /entity/notes/<id>/_upload ; PUT <links.upload> ; POST <links.complete_upload>`

**Docs claim** Silent. Probe 125 found a PUT sent at 910 s refused; probe 140 left the long PUT open.

**Actual**

```
one URL per PUT, minted at t0, X-Amz-Expires 900; one connection, a fixed Content-Length,
then 512 bytes every 5 s until about t0+963 s

run  headers at  sent at once  body bytes  last byte  answer                      runs
A    2 to 4 s    512 B         98816       963-965 s  200                         3 of 3
E    600 s       512 B         37376       961 s      403 Request has expired     2 of 2
B    861 s       512 B         10752       961 s      403 Request has expired     3 of 3
D    860 s       64 KiB        76288       961 s      403 Request has expired     2 of 2
F    861 s       256 KiB       272896      961 s      403 Request has expired     1 of 1
G    861 s       1 MiB         1059328     961 s      403 Request has expired     1 of 1

each 403, the S3 body, sent once the last byte was in:
<Error><Code>AccessDenied</Code><Message>Request has expired</Message><X-Amz-Expires>900</X-Amz-Expires>
<Expires>2026-11-17T16:17:14Z</Expires><ServerTime>2026-11-17T16:18:15Z</ServerTime>...</Error>

A: complete_upload -> 201; GET Range bytes=-1 -> 206 Content-Range bytes 98815-98815/98816
```

**Teaches**
- The expiry is not checked against the moment a PUT starts: E sent its headers 300 s before the
  URL expired and was refused after its last byte, `ServerTime` 61 s past `Expires`.
- A PUT started at once may outlast the URL: A ended 63 s past expiry and the stored object read
  back at the bytes sent. Where between 4 s and 600 s a start stops being safe is unmeasured.
- Sending more up front did not help a late start: 64 KiB, 256 KiB and 1 MiB at 861 s were all
  refused at the end.
- Call `_upload` right before the PUT and start it at once. An upload that may run past 900 s goes
  up in parts, each part URL minted when its part is sent (probes 044, 139).
