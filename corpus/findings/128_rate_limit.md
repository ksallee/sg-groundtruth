---
tags: [header, protocol, cost]
endpoints: [GET /entity/<type>]
phase: protocol
scope: api
measured: site-wide, 2026-11-11; 80 read-only GETs, the largest burst 60 from 10 threads in 1.9 s
coverage: partial
unmeasured: the load at which a limit bites, if one exists. The burst was kept small on a shared site. Blocked on the work
verdict: 60 GETs from 10 threads in 1.9 s all answered 200 with no rate-limit header of any kind. Code a backoff on 429 and 503 without having seen either.
---

# 128_rate_limit

**Q** Does the REST API rate-limit a client, and with what status and headers?

**Endpoint** `GET /entity/<type>`

**Docs claim** Silent in the REST reference. No limit, status or header is named.

**Actual**

```
60 x GET /entity/projects?page[size]=1&fields=id, 10 threads
  60 in 1.9 s (30.8/s); statuses {200: 60}; latency min 0.26 s, median 0.29 s, max 0.49 s
20 x the same, one thread, back to back
  20 in 5.8 s (3.5/s); statuses {200: 20}; latency min 0.26 s, median 0.28 s, max 0.38 s

headers naming ratelimit, rate-limit, retry-after, x-throttle or quota: none
every response header: cache-control connection content-encoding content-type date etag
  server set-cookie status strict-transport-security transfer-encoding vary
  x-content-type-options x-frame-options x-request-id x-xss-protection
```

**Teaches**
- At about 30 requests a second from one script there is no throttling and no header that would
  announce one, so a client cannot read a budget before it hits it.
- Latency was flat across the burst: the median at 10 threads matched the single-thread one.
- What a limit would answer is unmeasured. Retry 429 and 503 with exponential backoff and honour a
  `Retry-After` if one ever appears; do not assume any other status means "slow down".
