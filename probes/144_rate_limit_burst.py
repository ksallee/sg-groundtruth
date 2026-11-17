"""Q: what does the REST API answer when it rate-limits a client: status, headers, `Retry-After`?

Probe 128 saw no limit and no header at 60 GETs in 1.9 s. sg-onset drains a day of captures in one
go, reads and writes mixed. This sends a larger burst, still bounded: 300 requests from 20 threads,
paced to about 10 s, each one of a `GET` of one project, a `_search` on the sandbox, or a `PUT` of
`description` on one of 20 throwaway rows. Every worker stops at the first 429 or 503, and that
answer is printed whole. Any header naming a limit is printed wherever it appears.

Writes in the sandbox, behind `--write`: 20 rows `zzprobe_144_*` on the first enabled custom slot,
deleted on exit.

    python probes/144_rate_limit_burst.py --write
"""
import collections
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

import _lib

ARR = "application/vnd+shotgun.api3_array+json"
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 144 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
schema = c.get("/schema").json()["data"]
CE = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())[0]
SLUG = f"custom_entity{CE[12:]}s"
N, THREADS, SPAN = 300, 20, 10.0
LIMITY = ("ratelimit", "rate-limit", "retry-after", "x-throttle", "quota", "x-ratelimit")
rows = []
stop = threading.Event()


def out(s=""):
    rows.append(str(s))


with _lib.Created(c) as made:
    ids = [made.add(SLUG, c.post(f"/entity/{SLUG}", json={"project": P, "code": f"zzprobe_144_{i:02d}"}).json()["data"]["id"])
           for i in range(20)]
    c.get("/entity/projects", params={"page[size]": 1})  # mint the bearer outside the burst
    H = {"Authorization": f"Bearer {c._token}", "Accept": "application/json"}
    base = f"{c.site}/api/v1"
    t0 = time.time()

    def one(i):
        due = t0 + SPAN * i / N
        time.sleep(max(0, due - time.time()))
        if stop.is_set():
            return None
        kind = ("get", "search", "put")[i % 3]
        t = time.time()
        if kind == "get":
            r = requests.get(f"{base}/entity/projects", params={"page[size]": 1, "fields": "id"}, headers=H, timeout=60)
        elif kind == "search":
            r = requests.post(f"{base}/entity/{SLUG}/_search", headers={**H, "Content-Type": ARR}, timeout=60,
                              json={"filters": [["project", "is", P], ["code", "starts_with", "zzprobe_144_"]],
                                    "fields": ["code"], "page": {"size": 5}})
        else:
            r = requests.put(f"{base}/entity/{SLUG}/{ids[i % 20]}", headers=H, timeout=60,
                             json={"description": f"zzprobe_144 {i}"})
        if r.status_code in (429, 503):
            stop.set()
        return kind, r.status_code, time.time() - t, t - t0, {k.lower(): v for k, v in r.headers.items()}, r.text[:600]

    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        res = [x for x in pool.map(one, range(N)) if x]
    wall = time.time() - t0

    out(f"===== {len(res)} of {N} requests sent, {THREADS} threads, in {wall:.1f} s ({len(res) / wall:.1f}/s)")
    by = collections.defaultdict(collections.Counter)
    for kind, st, *_ in res:
        by[kind][st] += 1
    for kind in ("get", "search", "put"):
        lat = sorted(d for k, _, d, *_ in res if k == kind)
        if lat:
            out(f"  {kind:<6} statuses {dict(by[kind])}; latency min {lat[0]:.2f}s median {lat[len(lat) // 2]:.2f}s max {lat[-1]:.2f}s")
    per_s = collections.Counter(int(at) for *_, at, _, _ in [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in res])
    out(f"  sent per second of the burst: {[per_s[s] for s in sorted(per_s)]}")
    lim = sorted({f"{k}: {v}" for *_, h, _ in res for k, v in h.items() if any(w in k for w in LIMITY)})
    out(f"  headers naming a limit: {lim or 'none'}")
    names = sorted({k for *_, h, _ in res for k in h})
    out(f"  every response header name: {names}")
    bad = [r for r in res if r[1] >= 400]
    for kind, st, d, at, h, body in bad[:3]:
        out(f"  first non-2xx: {kind} {st} at +{at:.1f}s {body}")
    out(f"  stopped on a limit: {stop.is_set()}")
    wrote = sum(1 for i in ids if (c.get(f"/entity/{SLUG}/{i}", params={"fields": "description"}).json()["data"]["attributes"]["description"] or "").startswith("zzprobe_144"))
    out(f"  throwaway rows holding a burst write: {wrote} of 20")
    _lib.emit("144_rate_limit_burst", "\n".join(rows), env)
