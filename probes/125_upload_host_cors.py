"""Q: can a browser page PUT to the presigned upload host, read the part ETag, and read the file
back, and how long is a presigned URL good for?

Probe 062 measured CORS on `/api/v1` and stopped at the presigned host, which is not the site. This
sends the requests a browser would send to the URLs `_upload` hands out, with an `Origin` header, and
reads the answer's CORS headers: the preflight (`OPTIONS` with `Access-Control-Request-Method: PUT`),
the PUT itself, a multipart part PUT whose `ETag` the page has to collect (probe 044), and a GET of
the stored file.

A process can read every header and is never blocked, so this proves what the host answers, not
what a browser does with it. A browser refuses a response whose `access-control-allow-origin`
matches neither the page's origin nor `*`, and lets script read a header only if it is safelisted or
named in `access-control-expose-headers`.

Writes: one Version `zzprobe_125` in the sandbox and the Attachment its upload makes, deleted on exit.
The multipart init is aborted.

    python probes/125_upload_host_cors.py --write
"""
import json
import os
import re
import urllib.parse

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
if not _lib.writes_allowed():
    raise SystemExit("125_upload_host_cors writes to the site; re-run with --write")
ORIGINS = ("https://example.invalid", "http://localhost:5173", "null")
CORS = ("access-control-allow-origin", "access-control-allow-credentials",
        "access-control-allow-methods", "access-control-allow-headers",
        "access-control-expose-headers", "access-control-max-age", "vary")
rows = []


def out(s=""):
    rows.append(str(s))


def host(url):
    """The host with any bucket or account label masked: the shape teaches, the name does not."""
    h = urllib.parse.urlparse(url).netloc
    return re.sub(r"^[^.]+\.(s3[.-])", r"<bucket>.\1", h)


def query_keys(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return {k: (q[k][0] if k in ("X-Amz-Expires", "X-Amz-Algorithm", "X-Amz-SignedHeaders") else "...")
            for k in sorted(q)}


def show(label, r):
    h = {k.lower(): v for k, v in r.headers.items()}
    got = {k: h[k] for k in CORS if k in h}
    out(f"  {label}: {r.status_code}" + ("" if got else "  no CORS header"))
    for k, v in got.items():
        out(f"      {k}: {v}")
    return h


SB = _lib.sandbox_id(c, env)
with _lib.Created(c) as made:
    v = made.add("versions", c.post("/entity/versions", json={
        "project": {"type": "Project", "id": SB}, "code": "zzprobe_125"}).json()["data"]["id"])
    FIELD = f"/entity/versions/{v}/sg_uploaded_movie/_upload"
    b = c.get(FIELD, params={"filename": "zzprobe_125.jpg"}).json()
    up = b["links"]["upload"]
    out(f"===== the single-PUT URL: host {host(up)}, scheme {urllib.parse.urlparse(up).scheme}")
    out(f"  query keys: {json.dumps(query_keys(up))}")

    out("\n===== preflight, OPTIONS on the upload URL")
    for o in ORIGINS:
        show(f"Origin {o}, ACRM PUT, ACRH content-type",
             requests.options(up, headers={"Origin": o, "Access-Control-Request-Method": "PUT",
                                           "Access-Control-Request-Headers": "content-type"}, timeout=30))
    show("Origin https://example.invalid, ACRM PUT, no ACRH",
         requests.options(up, headers={"Origin": ORIGINS[0], "Access-Control-Request-Method": "PUT"},
                          timeout=30))
    show("Origin https://example.invalid, ACRM PUT, ACRH content-type,x-amz-meta-probe",
         requests.options(up, headers={"Origin": ORIGINS[0], "Access-Control-Request-Method": "PUT",
                                       "Access-Control-Request-Headers": "content-type,x-amz-meta-probe"},
                          timeout=30))

    out("\n===== the PUT itself, with Origin and Content-Type: image/jpeg")
    body = os.urandom(2048)
    put = requests.put(up, data=body, headers={"Origin": ORIGINS[0], "Content-Type": "image/jpeg"},
                       timeout=60)
    h = show("PUT", put)
    out(f"      etag present: {'etag' in h}; every response header name: {sorted(h)}")
    cr = c.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}})
    out(f"  complete_upload -> {cr.status_code}")

    out("\n===== the stored file read back: GET the presigned download URL with Origin")
    um = c.get(f"/entity/versions/{v}", params={"fields": "sg_uploaded_movie"}).json()["data"]["attributes"]["sg_uploaded_movie"] or {}
    if um.get("id"):
        made.rows.insert(0, ("attachments", um["id"]))
    dl = um.get("url")
    if dl:
        g0 = requests.get(dl, timeout=60, allow_redirects=False)
        out(f"  sg_uploaded_movie.url host {host(dl)}; GET without following -> {g0.status_code}"
            + (f", Location host {host(g0.headers['location'])}" if "location" in {k.lower() for k in g0.headers} else ""))
        target = g0.headers.get("location", dl) if g0.is_redirect else dl
        out(f"  final URL query keys: {json.dumps(query_keys(target))}")
        g = requests.get(dl, headers={"Origin": ORIGINS[0]}, timeout=60)
        show(f"GET with Origin (redirects followed), {len(g.content)} b, identical {g.content == body}", g)
        show("OPTIONS preflight on the final URL, ACRM GET",
             requests.options(target, headers={"Origin": ORIGINS[0], "Access-Control-Request-Method": "GET"},
                              timeout=30))

    out("\n===== a multipart part: the ETag a page must collect (probe 044)")
    m = c.get(FIELD, params={"filename": "zzprobe_125_mp.bin", "multipart_upload": "true"}).json()
    part_url = m["links"]["upload"]
    out(f"  part URL host {host(part_url)}; query keys {json.dumps(query_keys(part_url))}")
    show("OPTIONS on the part URL, ACRM PUT",
         requests.options(part_url, headers={"Origin": ORIGINS[0], "Access-Control-Request-Method": "PUT"},
                          timeout=30))
    pp = requests.put(part_url, data=os.urandom(1024), headers={"Origin": ORIGINS[0]}, timeout=60)
    h = show("part PUT with Origin", pp)
    out(f"      etag on the response: {'etag' in h}; exposed to script: "
        f"{'etag' in h.get('access-control-expose-headers', '').lower()}")
    ab = c.post(f"{FIELD}/multipart_abort", json=m["data"])
    out(f"  multipart_abort -> {ab.status_code}")

    out("\n===== the API's own upload calls, preflighted from a page (probe 062 covers /api/v1)")
    site = env["FPT_API_SITE_URL"].rstrip("/")
    show("OPTIONS <site>/api/v1/entity/versions/<id>/sg_uploaded_movie/_upload, ACRM GET, ACRH authorization",
         requests.options(f"{site}/api/v1{FIELD}", headers={
             "Origin": ORIGINS[0], "Access-Control-Request-Method": "GET",
             "Access-Control-Request-Headers": "authorization"}, timeout=30))

    if "--expiry" in __import__("sys").argv:
        # X-Amz-Expires says 900. The URL also carries an STS security token with a lifetime of its
        # own, so the signed number is a claim until a PUT past it is refused.
        import time
        out("\n===== --expiry: two upload URLs minted together, one PUT at 840 s, the other at 910 s")
        b2 = c.get(FIELD, params={"filename": "zzprobe_125_late.bin"}).json()
        b3 = c.get(FIELD, params={"filename": "zzprobe_125_late2.bin"}).json()
        t0 = time.time()
        time.sleep(840)
        r1 = requests.put(b2["links"]["upload"], data=b"x" * 16, timeout=60)
        out(f"  PUT at {time.time() - t0:.0f}s -> {r1.status_code}")
        time.sleep(max(0, 910 - (time.time() - t0)))
        r2 = requests.put(b3["links"]["upload"], data=b"x" * 16, timeout=60)
        out(f"  PUT at {time.time() - t0:.0f}s -> {r2.status_code} {r2.text[:300]}")
        # neither is completed: a single-PUT init opens nothing on the site (probe 039)

    _lib.emit("125_upload_host_cors", "\n".join(rows), env)
