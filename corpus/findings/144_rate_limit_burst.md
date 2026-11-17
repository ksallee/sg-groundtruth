---
tags: [header, protocol, cost, write]
endpoints: [GET /entity/<type>, POST /entity/<type>/_search, PUT /entity/<type>/<id>]
phase: protocol
scope: api
measured: sandbox project written, 2026-11-11; 300 mixed requests from 20 threads in 10.7 s, 20 throwaway rows deleted
coverage: partial
unmeasured: the load at which a limit bites, if one exists. The burst was capped at about 30/s on a shared site. Blocked on the work
verdict: 300 mixed reads and writes at 28 per second for 10 s all answered 200 with no rate-limit header. Median latency doubled from 0.3 s to 0.6 s instead. Back off on latency, not on a status.
---

# 144_rate_limit_burst

**Q** What does the REST API answer when it rate-limits a client: status, headers, `Retry-After`?

**Endpoint** `GET /entity/<type> ; POST /entity/<type>/_search ; PUT /entity/<type>/<id>`

**Docs claim** Silent. Probe 128 saw no limit at 60 GETs in 1.9 s.

**Actual**

```
300 requests, 20 threads, paced over 10 s, a third each:
  GET /entity/projects?page[size]=1, _search on 20 sandbox rows, PUT description on one of them
300 sent in 10.7 s (28.2/s); per second of the burst [30, 29, 31, 30, 30, 30, 30, 30, 28, 30, 2]
  get     {200: 100}  latency min 0.28 s  median 0.61 s  max 0.79 s
  search  {200: 100}  latency min 0.27 s  median 0.60 s  max 0.85 s
  put     {200: 100}  latency min 0.32 s  median 0.66 s  max 0.85 s
headers naming ratelimit, rate-limit, retry-after, x-throttle or quota: none
every response header: cache-control connection content-encoding content-type date etag server
  set-cookie status strict-transport-security transfer-encoding vary x-content-type-options
  x-frame-options x-request-id x-xss-protection
stopped on a 429 or 503: no; all 20 rows held a burst write afterwards
```

**Teaches**
- At 30 requests a second sustained for 10 s, mixed reads and writes, nothing is refused and nothing
  announces a budget. The limit answer is still unseen; code a backoff on 429 and 503 and honour a
  `Retry-After` if one appears (probe 128).
- The cost of load showed as latency: the median was 0.29 s for 60 GETs from 10 threads (probe 128)
  and 0.6 s here. A drain loop that watches its own latency and narrows its concurrency when it rises
  is the signal this site gives.
