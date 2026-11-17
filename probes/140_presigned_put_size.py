"""Q: what is the largest single presigned `PUT` the upload host accepts, and how long does it take?

Probe 044 found nothing in the API refuses a single-PUT upload for its size; S3 documents 5 GB as the
ceiling of one PUT. sg-onset decides when to switch to multipart. This steps up, one size at a time,
and stops at the first refusal, at 1 GB, or once a step would take longer than `--budget` seconds
(default 300) at the rate the previous one ran: 50 MB, 200 MB, 1 GB. The bytes are zeros from a
sparse temp file, so the client spends nothing building them; the host stores what it is sent.

Each upload is field-less onto one Note (probe 123), completed, read back for its size, and its
Attachment deleted at once.

Writes in the sandbox, behind `--write`: one Note `zzprobe_140`, one Attachment per size, deleted.

    python probes/140_presigned_put_size.py --write [--budget 300]
"""
import json
import os
import sys
import tempfile
import time

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 140 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
BUDGET = float(sys.argv[sys.argv.index("--budget") + 1]) if "--budget" in sys.argv else 300.0
MB = 1000 * 1000
SIZES = [50 * MB, 200 * MB, 1000 * MB]
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


tmp = tempfile.mkdtemp(prefix="zzprobe_140_")
with _lib.Created(c) as made:
    note = made.add("notes", c.post("/entity/notes", json={
        "project": P, "subject": "zzprobe_140", "content": "zzprobe_140"}).json()["data"]["id"])
    rate = None
    for size in SIZES:
        if rate and size / rate > BUDGET:
            out(f"  {size // MB} MB skipped: about {size / rate:.0f} s at the last rate, over the {BUDGET:.0f} s budget")
            break
        path = os.path.join(tmp, "zz.bin")
        with open(path, "wb") as f:
            f.truncate(size)
        name = f"zzprobe_140_{size // MB}MB.bin"
        i = c.get(f"/entity/notes/{note}/_upload", params={"filename": name}).json()
        t0 = time.time()
        with open(path, "rb") as f:
            try:
                put = requests.put(i["links"]["upload"], data=f, headers={"Content-Length": str(size)},
                                   timeout=(30, 3600))
                st, body = put.status_code, put.text[:400]
            except requests.RequestException as e:
                st, body = type(e).__name__, str(e)[:300]
        dt = time.time() - t0
        os.remove(path)
        out(f"===== {size // MB} MB: PUT -> {st} in {dt:.1f} s ({size / MB / dt:.1f} MB/s)" + ("" if st == 200 else f"\n  {body}"))
        if st != 200:
            break
        rate = size / dt
        cr = c.post(i["links"]["complete_upload"], json={"upload_info": i["data"], "upload_data": {}})
        atts = c.get(f"/entity/notes/{note}", params={"fields": "attachments"}).json()["data"]["relationships"]["attachments"]["data"]
        for a in atts:
            d = c.get(f"/entity/attachments/{a['id']}", params={"fields": "filename,file_size,this_file"}).json()["data"]["attributes"]
            if d.get("filename") != name:
                continue
            url = (d.get("this_file") or {}).get("url")
            # the last byte, not a HEAD: the URL is signed for GET and a HEAD is 403 (probe 141)
            h = requests.get(url, headers={"Range": "bytes=-1"}, timeout=60) if url else None
            out(f"  complete -> {cr.status_code}; file_size {d.get('file_size')!r}; "
                f"GET Range bytes=-1 -> {h.status_code if h is not None else '-'} Content-Range {h.headers.get('Content-Range') if h is not None else '-'}")
            r = c.delete(f"/entity/attachments/{a['id']}")
            out(f"  Attachment deleted -> {r.status_code}")
    _lib.emit("140_presigned_put_size", "\n".join(rows), env)
os.rmdir(tmp)
