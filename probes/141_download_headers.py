"""Q: does the stored file's GET (an Attachment's `this_file.url`) send `Content-Length`, can a page
read it and the body under CORS, does it honour `Range`, and can the body be cancelled after the
headers?

Probe 125 read a stored file back once, under an `Origin`, and found `access-control-allow-origin: *`
with only `ETag` exposed. sg-onset downloads photos in a page, shows progress from the length and
abandons a download the user scrolls away from. Measured on a 20 MB Attachment uploaded field-less to
a Note (probe 123):

  1. `GET this_file.url` with an `Origin`: every response header, the CORS ones and the length
  2. `HEAD` on the same URL (probe 140 saw 403)
  3. a preflight for a `Range` request header, and `Range: bytes=0-1023` itself
  4. the body streamed: time to headers, then the connection closed after 64 KiB
  5. `GET /entity/attachments/<id>/this_file` on `/api/v1`, for the shape the API itself answers

A process reads every header and no CORS rule binds it; a browser applies the rules to what it reads
here. Writes in the sandbox, behind `--write`: one Note `zzprobe_141` and its Attachment, deleted.

    python probes/141_download_headers.py --write
"""
import json
import os
import re
import time
import urllib.parse

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 141 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
ORIGIN = "https://example.invalid"
SIZE = 20 * 1000 * 1000
rows = []


def out(s=""):
    rows.append(str(s))


def host(url):
    h = urllib.parse.urlparse(url).netloc
    return re.sub(r"^[^.]+\.(s3[.-])", r"<bucket>.\1", h)


def hdrs(r, label):
    h = {k.lower(): v for k, v in r.headers.items()}
    out(f"  {label}: {r.status_code}")
    for k in sorted(h):
        if k in ("x-amz-request-id", "x-amz-id-2", "date", "etag", "last-modified", "x-amz-cf-id"):
            continue
        out(f"      {k}: {h[k][:120]}")
    return h


with _lib.Created(c) as made:
    note = made.add("notes", c.post("/entity/notes", json={
        "project": P, "subject": "zzprobe_141", "content": "zzprobe_141"}).json()["data"]["id"])
    i = c.get(f"/entity/notes/{note}/_upload", params={"filename": "zzprobe_141.jpg"}).json()
    body = os.urandom(SIZE)
    requests.put(i["links"]["upload"], data=body, timeout=600)
    c.post(i["links"]["complete_upload"], json={"upload_info": i["data"], "upload_data": {}})
    aid = c.get(f"/entity/notes/{note}", params={"fields": "attachments"}).json()["data"]["relationships"]["attachments"]["data"][0]["id"]
    made.rows.insert(0, ("attachments", aid))
    a = c.get(f"/entity/attachments/{aid}", params={"fields": "this_file,file_size"}).json()["data"]["attributes"]
    url = a["this_file"]["url"]
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    out(f"this_file.url host {host(url)}; X-Amz-Expires {q.get('X-Amz-Expires', ['-'])[0]}; "
        f"this_file keys {sorted(a['this_file'])}; file_size {a.get('file_size')!r}")

    out("\n===== 1. GET with Origin, body read whole")
    t0 = time.time()
    g = requests.get(url, headers={"Origin": ORIGIN}, timeout=300)
    h = hdrs(g, f"GET, {len(g.content)} b in {time.time() - t0:.1f}s, identical {g.content == body}")

    out("\n===== 2. HEAD")
    hdrs(requests.head(url, headers={"Origin": ORIGIN}, timeout=60), "HEAD")

    out("\n===== 3. Range")
    hdrs(requests.options(url, headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET",
                                        "Access-Control-Request-Headers": "range"}, timeout=60),
         "OPTIONS, ACRM GET, ACRH range")
    rg = requests.get(url, headers={"Origin": ORIGIN, "Range": "bytes=0-1023"}, timeout=60)
    hdrs(rg, f"GET Range bytes=0-1023, {len(rg.content)} b, equal to the first KiB {rg.content == body[:1024]}")

    out("\n===== 4. streamed, closed after 64 KiB")
    t0 = time.time()
    s = requests.get(url, headers={"Origin": ORIGIN}, stream=True, timeout=60)
    th = time.time() - t0
    got = 0
    for chunk in s.iter_content(16384):
        got += len(chunk)
        if got >= 65536:
            break
    s.close()
    out(f"  headers after {th:.2f}s, status {s.status_code}, content-length {s.headers.get('Content-Length')}; "
        f"read {got} b then closed at {time.time() - t0:.2f}s")
    g2 = requests.get(url, headers={"Origin": ORIGIN, "Range": "bytes=-16"}, timeout=60)
    out(f"  the same URL again after the cancel: Range bytes=-16 -> {g2.status_code}, {len(g2.content)} b")

    out("\n===== 5. the API's own field read")
    r = c.get(f"/entity/attachments/{aid}/this_file", allow_redirects=False)
    out(f"  GET /entity/attachments/<id>/this_file -> {r.status_code}; content-type {r.headers.get('Content-Type')}; "
        + (f"location host {host(r.headers['Location'])}" if "Location" in r.headers else
           f"body keys {sorted(r.json().get('data', {}) or {}) if 'json' in r.headers.get('Content-Type', '') else len(r.content)}"))
    _lib.emit("141_download_headers", "\n".join(rows), env)
