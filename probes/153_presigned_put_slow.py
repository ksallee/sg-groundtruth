"""Q: is a presigned PUT that starts inside the URL's 900 s and ends after it accepted?

Probe 125 found a PUT sent at 910 s refused with 403 `Request has expired`, and probe 140 left open
whether a PUT that started in time and finished late counts. sg-onset uploads video from an iPad on set
Wi-Fi, where one PUT can outlast the window.

Field-less uploads onto one Note (probe 123), each with its own URL, the body trickled in 512-byte
writes every 5 s over one connection with a fixed `Content-Length` (S3 refuses a chunked PUT):

    A  PUT starts at once, the last byte goes at about 965 s
    B  PUT starts at 860 s, the last byte goes at about 965 s
    D  PUT starts at 860 s, 64 KiB sent at once, then the trickle to about 965 s
    E  PUT starts at 600 s, the last byte goes at about 965 s
    F  PUT starts at 860 s, 256 KiB sent at once, then the trickle
    G  PUT starts at 860 s, 1 MiB sent at once, then the trickle

Each is completed if the PUT is 200 and read back with `Range: bytes=-1` (probe 140).

Writes in the sandbox, behind `--write`: one Note `zzprobe_153`, its Attachments, deleted on exit.

    python probes/153_presigned_put_slow.py --write
"""
import http.client
import os
import threading
import time
from urllib.parse import urlsplit

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 153 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
STEP, CHUNK, END = 5.0, 512, 965.0
rows, lock = [], threading.Lock()


def out(s=""):
    with lock:
        rows.append(str(s))
        print(s, flush=True)


def slow_put(url, t0, start_at, label, burst=0):
    """One PUT over one connection, `burst` bytes at once, then the rest a little at a time until END
    seconds after t0."""
    while time.time() - t0 < start_at:
        time.sleep(1)
    n = int((END - (time.time() - t0)) // STEP) + 1
    size = burst + n * CHUNK
    u = urlsplit(url)
    conn = http.client.HTTPSConnection(u.netloc, timeout=120)
    conn.putrequest("PUT", f"{u.path}?{u.query}", skip_accept_encoding=True)
    conn.putheader("Content-Length", str(size))
    conn.endheaders()
    first = time.time() - t0
    sent, err = 0, None
    try:
        if burst:
            conn.send(os.urandom(burst))
            sent += burst
        for k in range(n):
            conn.send(os.urandom(CHUNK))
            sent += CHUNK
            if k < n - 1:
                time.sleep(STEP)
    except OSError as e:
        err = f"{type(e).__name__}: {e}"
    last = time.time() - t0
    try:
        r = conn.getresponse()
        status, body = r.status, r.read().decode(errors="replace")
    except (OSError, http.client.HTTPException) as e:
        status, body = type(e).__name__, str(e)
    conn.close()
    out(f"{label}: headers sent at {first:.0f} s, {sent} of {size} bytes, last byte at {last:.0f} s"
        + (f", send error {err}" if err else "")
        + f"\n   PUT -> {status} at {time.time() - t0:.0f} s  {body.strip()}")
    return status, size


with _lib.Created(c) as made:
    note = made.add("notes", c.post("/entity/notes", json={
        "project": P, "subject": "zzprobe_153", "content": "zzprobe_153"}).json()["data"]["id"])
    runs = {}
    for label, start_at, burst in (("A", 2.0, 0), ("B", 860.0, 0), ("D", 860.0, 65536), ("E", 600.0, 0),
                                   ("F", 860.0, 262144), ("G", 860.0, 1048576)):
        name = f"zzprobe_153_{label}.bin"
        i = c.get(f"/entity/notes/{note}/_upload", params={"filename": name}).json()
        q = dict(p.split("=", 1) for p in urlsplit(i["links"]["upload"]).query.split("&"))
        runs[label] = {"name": name, "init": i, "t0": time.time(), "start_at": start_at, "burst": burst}
        out(f"{label}: URL minted, X-Amz-Expires {q.get('X-Amz-Expires')}, PUT to start at {start_at:.0f} s")

    res = {}
    threads = [threading.Thread(target=lambda L=L, r=r: res.__setitem__(
        L, slow_put(r["init"]["links"]["upload"], r["t0"], r["start_at"], L, r["burst"]))) for L, r in runs.items()]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for label, r in runs.items():
        status, size = res[label]
        if status != 200:
            continue
        cr = c.post(r["init"]["links"]["complete_upload"], json={"upload_info": r["init"]["data"], "upload_data": {}})
        atts = c.get(f"/entity/notes/{note}", params={"fields": "attachments"}).json()["data"]["relationships"]["attachments"]["data"]
        for a in atts:
            if ("attachments", a["id"]) not in made.rows:
                made.add("attachments", a["id"])
            d = c.get(f"/entity/attachments/{a['id']}", params={"fields": "filename,this_file"}).json()["data"]["attributes"]
            if d.get("filename") != r["name"]:
                continue
            g = requests.get(d["this_file"]["url"], headers={"Range": "bytes=-1"}, timeout=60)
            out(f"{label}: complete -> {cr.status_code}; GET Range bytes=-1 -> {g.status_code} "
                f"Content-Range {g.headers.get('Content-Range')} (sent {size})")
    _lib.emit("153_presigned_put_slow", "\n".join(rows), env)
