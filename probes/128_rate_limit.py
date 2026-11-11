"""Q: does the REST API rate-limit a client, and with what status and headers?

A sync client that drains a week of captures sends bursts. This sends a modest one, read-only, and
records every status and any header that names a limit: 60 `GET /entity/projects?page[size]=1` from
10 threads at once, then 20 back to back on one thread. It is deliberately small; the probed site is
shared, and a limit that only bites above this is not measured here.

Read-only.

    python probes/128_rate_limit.py
"""
import collections
import time
from concurrent.futures import ThreadPoolExecutor

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
c.get("/entity/projects", params={"page[size]": 1})  # mint the bearer once, outside the burst
URL = f"{c.site}/api/v1/entity/projects"
HEAD = {"Authorization": f"Bearer {c._token}", "Accept": "application/json"}
LIMITY = ("ratelimit", "rate-limit", "retry-after", "x-throttle", "quota")
rows = []


def one(_):
    t = time.time()
    r = requests.get(URL, params={"page[size]": 1, "fields": "id"}, headers=HEAD, timeout=60)
    return r.status_code, time.time() - t, {k.lower(): v for k, v in r.headers.items()}, r.text[:300]


def report(label, res, wall):
    statuses = collections.Counter(s for s, _, _, _ in res)
    lat = sorted(d for _, d, _, _ in res)
    names = sorted({k for _, _, h, _ in res for k in h})
    limit = sorted({f"{k}: {v}" for _, _, h, _ in res for k, v in h.items() if any(w in k for w in LIMITY)})
    rows.append(f"===== {label}")
    rows.append(f"  {len(res)} requests in {wall:.1f}s ({len(res) / wall:.1f}/s); statuses {dict(statuses)}")
    rows.append(f"  latency min {lat[0]:.2f}s median {lat[len(lat) // 2]:.2f}s max {lat[-1]:.2f}s")
    rows.append(f"  headers naming a limit: {limit or 'none'}")
    rows.append(f"  every response header name: {names}")
    for s, _, h, body in res:
        if s != 200:
            rows.append(f"  first non-200: {s} {body}")
            break


t0 = time.time()
with ThreadPoolExecutor(max_workers=10) as pool:
    res = list(pool.map(one, range(60)))
report("60 GETs, 10 threads", res, time.time() - t0)
t0 = time.time()
res = [one(i) for i in range(20)]
report("20 GETs, one thread, back to back", res, time.time() - t0)

_lib.emit("128_rate_limit", "\n".join(rows), env)
