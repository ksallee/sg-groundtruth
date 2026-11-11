"""Q: how long does a multipart `upload_id` live, is the `timestamp` in a part link checked for age,
and does a part URL minted 20 minutes after the init still complete?

Probe 044 measured the multipart flow in one sitting; probe 125 measured a presigned URL refused
after 900 s. sg-onset resumes an upload after the set loses its connection, possibly much later, so
it needs to know what of the init survives. Two uploads, field-less onto one Note (probe 123):

  M1  init at t0, part 1 (5 MiB) PUT at once. At t0 + `--wait` (default 1230 s): the part 1 URL
      PUT again, part 2 minted through `get_next_part` and PUT, and the upload completed.
  M2  init at t0, part 1 minted by `GET .../_upload/multipart` with the link's `timestamp`
      replaced by `2020-01-01T00:00:00Z`, PUT and completed at once.

Every refusal is printed whole. Writes in the sandbox, behind `--write`: one Note `zzprobe_139` and
the Attachments the completions make, deleted; an upload that does not complete is aborted.

    python probes/139_multipart_lifetime.py --write [--wait 1230]
"""
import json
import os
import sys
import time
import urllib.parse

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 139 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
WAIT = float(sys.argv[sys.argv.index("--wait") + 1]) if "--wait" in sys.argv else 1230.0
MIB5 = 5 * 1024 * 1024
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def errs(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))[:600]
    except ValueError:
        return repr(r.text[:400])


def query(url):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))


with _lib.Created(c) as made:
    note = made.add("notes", c.post("/entity/notes", json={
        "project": P, "subject": "zzprobe_139", "content": "zzprobe_139"}).json()["data"]["id"])
    base = f"/entity/notes/{note}/_upload"
    t0 = time.time()

    def el():
        return f"t0+{time.time() - t0:.0f}s"

    m1 = c.get(base, params={"filename": "zzprobe_139_m1.bin", "multipart_upload": "true"}).json()
    out(f"===== M1 init {el()}: data keys {sorted(m1['data'])}, timestamp {m1['data']['timestamp']}")
    out(f"  get_next_part query keys: {sorted(query(m1['links']['get_next_part']))}")
    p1_url = m1["links"]["upload"]
    p1 = requests.put(p1_url, data=os.urandom(MIB5), timeout=300)
    out(f"  part 1 PUT {el()} -> {p1.status_code}, etag {'present' if p1.headers.get('ETag') else 'absent'}")
    etags = [p1.headers.get("ETag")]

    out(f"\n===== M2 init {el()}, part 1 minted with the timestamp replaced")
    m2 = c.get(base, params={"filename": "zzprobe_139_m2.bin", "multipart_upload": "true"}).json()
    q = query(m2["links"]["get_next_part"])
    real = q["timestamp"]
    for label, ts in (("timestamp 2020-01-01T00:00:00Z", "2020-01-01T00:00:00Z"), ("timestamp garbage", "zz"),
                      ("timestamp omitted", None), ("the init's own timestamp (control)", real)):
        params = {**q, "part_number": "1"}
        if ts is None:
            params.pop("timestamp")
        else:
            params["timestamp"] = ts
        r = c.get(f"{base}/multipart", params=params)
        out(f"  GET …/_upload/multipart {label} -> {r.status_code} {'' if r.ok else errs(r)}")
        if r.ok:
            u = r.json()["links"]["upload"]
            out(f"    URL path differs from the control's: {urllib.parse.urlparse(u).path != urllib.parse.urlparse(m2['links']['upload']).path}; "
                f"X-Amz-Date {query(u).get('X-Amz-Date')}")
            pp = requests.put(u, data=os.urandom(1024), timeout=60)
            out(f"    PUT -> {pp.status_code} {pp.text[:300] if not pp.ok else ''}")
            if not pp.ok:
                continue
            info = {**m2["data"], "etags": [pp.headers.get("ETag")]}
            cr = c.post(m2["links"]["complete_upload"], json={"upload_info": info, "upload_data": {}})
            out(f"    complete with the init's own upload_info -> {cr.status_code} {'' if cr.ok else errs(cr)}")
            m2 = None if cr.ok else m2
    if m2:
        ab = c.post(f"{base}/multipart_abort", json=m2["data"])
        out(f"  M2 aborted -> {ab.status_code}")
    done = False
    if "--m2" in sys.argv:
        out("\n===== --m2: M1 is not waited on")
    else:
        out(f"\n===== waiting until t0+{WAIT:.0f}s")
        time.sleep(max(0, WAIT - (time.time() - t0)))
        r = requests.put(p1_url, data=os.urandom(1024), timeout=60)
        out(f"  M1 part 1 URL PUT again {el()} -> {r.status_code} {r.text[:200] if not r.ok else ''}")
        g = c.get(m1["links"]["get_next_part"])
        out(f"  M1 get_next_part {el()} -> {g.status_code} {'' if g.ok else errs(g)}")
        if g.ok:
            p2 = requests.put(g.json()["links"]["upload"], data=os.urandom(2048), timeout=60)
            out(f"  part 2 PUT {el()} -> {p2.status_code} {p2.text[:300] if not p2.ok else ''}")
            etags.append(p2.headers.get("ETag"))
            cr = c.post(m1["links"]["complete_upload"], json={"upload_info": {**m1["data"], "etags": etags},
                                                               "upload_data": {}})
            out(f"  complete {el()} -> {cr.status_code} {'' if cr.ok else errs(cr)}")
            done = cr.ok
    if not done:
        ab = c.post(f"{base}/multipart_abort", json=m1["data"])
        out(f"  M1 aborted -> {ab.status_code} {'' if ab.ok else errs(ab)}")

    atts = c.get(f"/entity/notes/{note}", params={"fields": "attachments"}).json()["data"]["relationships"]["attachments"]["data"]
    for a in atts:
        d = c.get(f"/entity/attachments/{a['id']}", params={"fields": "filename,this_file"}).json()["data"]["attributes"]
        url = (d.get("this_file") or {}).get("url")
        # a GET, not a HEAD: the URL is signed for GET and a HEAD is refused 403 (probe 140)
        h = requests.get(url, timeout=60, stream=True) if url else None
        if h is not None:
            h.close()
        out(f"  Attachment {d.get('filename')}: stored file GET -> {h.status_code if h is not None else '-'}, "
            f"Content-Length {h.headers.get('Content-Length') if h is not None else '-'}")
        made.rows.insert(0, ("attachments", a["id"]))
    _lib.emit("139_multipart_lifetime", "\n".join(rows), env)
