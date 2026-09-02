"""Q: how does media come out of Flow PT and go back in, and what does the round trip leave stale?

Every sync, transfer and hand-off does this. There is no server-side copy to test for: the only route
between two Versions is download the bytes and upload them again (probe 013).

Read-only half: enumerate the renditions on a Version that has them, pick one, measure the signature
window, work out where the file extension lives, and fetch the bytes.
--write half: clear a target Version's media and put the same bytes back, then read what stayed stale.
"""
import base64
import json
import os
import tempfile
import time
from urllib.parse import parse_qs, unquote, urlparse

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []

ARRAY = {"Content-Type": "application/vnd+shotgun.api3_array+json"}   # probe 004
JSON = {"Content-Type": "application/json"}

# Every field on a Version that can hold a rendition, plus the two the transcoder writes about them.
URL_FIELDS = ["sg_uploaded_movie", "sg_uploaded_movie_mp4", "sg_uploaded_movie_webm",
              "sg_uploaded_movie_image"]
IMAGE_FIELDS = ["image", "filmstrip_image"]
DERIVED = ["sg_uploaded_movie_frame_rate", "sg_uploaded_movie_transcoding_status"]
FIELDS = URL_FIELDS + IMAGE_FIELDS + DERIVED + ["code"]

# Transcoding is async: ~38s for a tiny png (probe 013), 75s for a movie (probe 022).
POLL = (0, 15, 25, 40, 60, 60)

# Transcoded before master: the mp4 is what the review player was given, is the smallest, and is the
# only rendition guaranteed to be a format the far end can open. The master is whatever was uploaded.
PREFERENCE = ["sg_uploaded_movie_mp4", "sg_uploaded_movie_webm", "sg_uploaded_movie_image",
              "sg_uploaded_movie", "image"]

# 16x16 red PNG, so the probe needs no image library and no file on disk (probe 013).
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAJ0lEQVR42mP8z8BQz0AEYBxVSF+F"
    "jIyM/xnpoxCfwlGFoy4cVUgPhQCq0Ass7T6l4wAAAABJRU5ErkJggg==")


def read(vid, fields=FIELDS):
    return c.get(f"/entity/versions/{vid}", params={"fields": ",".join(fields)}).json()["data"]["attributes"]


def url_of(value):
    """A rendition is a string (image) or an object (url). A link_type local object has no url at all."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and value.get("link_type") != "local":
        return value.get("url")
    return None


def disposition_filename(url):
    """The signature signs response-content-disposition, so the filename is inside the query string."""
    q = parse_qs(urlparse(url).query)
    cd = (q.get("response-content-disposition") or [""])[0]
    for part in cd.split(";"):
        part = part.strip()
        for key in ("filename*=UTF-8''", "filename="):
            if part.startswith(key):
                return unquote(part[len(key):].strip('"'))
    return None


def signature(url):
    q = parse_qs(urlparse(url).query)
    return {k: (q.get(k) or [""])[0] for k in ("X-Amz-Date", "X-Amz-Expires")}, sorted(q)


def download(url):
    """Bytes to a temp file. The caller removes it in a finally, even when the upload fails."""
    fd, path = tempfile.mkstemp(prefix="zzprobe_034_")
    r = requests.get(url, timeout=300)                       # HEAD is not signed; it 403s
    with os.fdopen(fd, "wb") as fh:
        fh.write(r.content)
    return path, r.status_code, r.headers.get("Content-Type"), len(r.content)


def upload(vid, field, filename, payload):
    """probe 013 — three steps, and upload_data is required even though it is empty."""
    b = c.get(f"/entity/versions/{vid}/{field}/_upload", params={"filename": filename}).json()
    put = requests.put(b["links"]["upload"], data=payload, timeout=300)
    r = c.post(b["links"]["complete_upload"], headers=JSON,
               json={"upload_info": b["data"], "upload_data": {}})
    if not r.ok:
        raise SystemExit(f"complete_upload {r.status_code}: {r.text}")
    return put.status_code, r.status_code, b["data"].get("upload_type")


def state(attrs):
    """One row per rendition field: what it holds and how a client tells."""
    out = []
    for f in URL_FIELDS + IMAGE_FIELDS:
        v = attrs.get(f)
        if v is None:
            out.append((f, "null", "", ""))
        elif isinstance(v, str):
            kind = "transcoding" if "/images/status/transient/" in v else "url str"
            out.append((f, kind, "", ""))
        else:
            out.append((f, f"link_type={v.get('link_type')}", v.get("name") or "",
                        f"{v.get('content_type')} Attachment {v.get('id')}"))
    for f in DERIVED:
        out.append((f, repr(attrs.get(f)), "", ""))
    return out


def table(title, attrs):
    rows.append(title)
    for f, st, name, extra in state(attrs):
        rows.append(f"  {f:<38} {st:<20} {name:<34} {extra}")


# ---------------------------------------------------------------- read-only: find a Version with media
source = None
for pid in _lib.sample_projects(c, env):
    r = c.post("/entity/versions/_search", headers=ARRAY, json={
        "filters": [["project", "is", {"type": "Project", "id": pid}], ["image", "is_not", None]],
        "fields": FIELDS, "page": {"size": 50}})
    cand = [d for d in r.json()["data"]
            if url_of(d["attributes"].get("sg_uploaded_movie_mp4"))]
    if not cand:
        cand = [d for d in r.json()["data"] if url_of(d["attributes"].get("image"))]
    if cand:
        # the richest row: the most renditions filled, so the table is worth reading
        source = max(cand, key=lambda d: sum(d["attributes"].get(f) is not None
                                             for f in URL_FIELDS + IMAGE_FIELDS))
        rows.append(f"source: Version {source['id']} on project {pid}, "
                    f"{len(cand)} of {len(r.json()['data'])} rows in the page carry a rendition")
        break
if source is None:
    raise SystemExit("no Version with media on any FPT_PROBE_SAMPLE_PROJECTS project")
_lib.note_from(source)
a = read(source["id"])
_lib.note_from(a)

table("\n=== 1. the renditions on that Version", a)

pick = next((f for f in PREFERENCE if url_of(a.get(f))), None)
src_url = url_of(a[pick])
rows.append(f"\n=== 2. chosen: {pick} — the transcode, not the master")

# ------------------------------------------------------------------------------ 3. the signature window
sig, names = signature(src_url)
rows.append("\n=== 3. the signed url")
rows.append(f"  query params: {names}")
rows.append(f"  X-Amz-Date={sig['X-Amz-Date']} X-Amz-Expires={sig['X-Amz-Expires']}s")
again = url_of(read(source["id"], [pick])[pick])
sig2, _ = signature(again)
rows.append(f"  re-read the field: identical string? {again == src_url}; "
            f"X-Amz-Date={sig2['X-Amz-Date']} X-Amz-Expires={sig2['X-Amz-Expires']}s")
h = requests.head(src_url, timeout=60)
rows.append(f"  HEAD {h.status_code} {h.headers.get('Content-Type')}   GET is the only signed method")

# ------------------------------------------------------------------------------------ 4. the filename
rows.append("\n=== 4. where the extension lives, on every filled rendition")
rows.append(f"  {'field':<38} {'name key':<34} {'response-content-disposition filename':<40}")
for f in URL_FIELDS + IMAGE_FIELDS:
    u = url_of(a.get(f))
    if not u:
        continue
    n = a[f].get("name") if isinstance(a[f], dict) else None
    d = disposition_filename(u)
    _lib.note_names(n or "", d or "")
    rows.append(f"  {f:<38} {str(n):<34} {str(d):<40} ext={os.path.splitext(d or '')[1]!r}")
att_name = a[pick].get("name") if isinstance(a[pick], dict) else None
cd_name = disposition_filename(src_url)
filename = cd_name or att_name or "media.bin"

# --------------------------------------------------------------------------------------- 5. download
path, code, ctype, size = download(src_url)
try:
    rows.append(f"\n=== 5. GET the bytes -> {code} {ctype} {size}b -> {os.path.basename(path)}")

    if not _lib.writes_allowed():
        rows.append("\n(read-only: re-run with --write for the upload half)")
    else:
        # ------------------------------------------------------- 6. put it back on a sandbox Version
        SANDBOX = _lib.sandbox_id(c, env)
        with _lib.Created(c) as made:
            t = c.post("/entity/versions", headers=JSON, json={
                "project": {"type": "Project", "id": SANDBOX},
                "code": "zzprobe_034_target",
                "description": "probe 034 — media round trip",
            }).json()["data"]
            tid = made.add("versions", t["id"])
            rows.append(f"\n=== 6. target Version {tid} in the sandbox")

            def settle(label):
                for wait in POLL:
                    time.sleep(wait)
                    a2 = read(tid)
                    if a2.get("sg_uploaded_movie_transcoding_status") in (1, 2):
                        break
                rows.append(f"  {label}: status="
                            f"{a2.get('sg_uploaded_movie_transcoding_status')} after ~"
                            f"{sum(POLL[:1 + POLL.index(wait)])}s")
                return a2

            # a generated 16x16 png in the media field: does the transcoder take one?
            rows.append(f"\n  seed with a generated png -> {upload(tid, 'sg_uploaded_movie', 'zzprobe_034_seed.png', PNG)}")
            table("  after the seed transcode", settle("seed"))

            with open(path, "rb") as fh:
                payload = fh.read()
            rows.append(f"\n  first sync: upload {filename} ({len(payload)}b) -> "
                        f"{upload(tid, 'sg_uploaded_movie', filename, payload)}")
            table("  after the first sync transcode", settle("first sync"))

            rows.append("\n  re-sync. clear the media field alone, the way a naive job does")
            r1 = c.put(f"/entity/versions/{tid}", headers=JSON, json={"sg_uploaded_movie": None})
            table(f"  after PUT sg_uploaded_movie null -> {r1.status_code}", read(tid))

            r2 = c.put(f"/entity/versions/{tid}", headers=JSON,
                       json={f: None for f in URL_FIELDS + IMAGE_FIELDS})
            table(f"\n  after PUT every rendition field null -> {r2.status_code}", read(tid))

            rows.append(f"\n  upload the same bytes back -> "
                        f"{upload(tid, 'sg_uploaded_movie', filename, payload)}")
            table("  immediately after the 201", read(tid))
            done = settle("re-sync")
            table("  after the re-sync transcode", done)

            src_bytes = len(payload)
            back = url_of(done.get("sg_uploaded_movie"))
            if back:
                rt = requests.get(back, timeout=300)
                rows.append(f"\n  fetch what came back -> {rt.status_code} {rt.headers.get('Content-Type')} "
                            f"{len(rt.content)}b; identical to what was uploaded? {rt.content == payload} "
                            f"(sent {src_bytes}b)")

            att = c.post("/entity/attachments/_search", headers=ARRAY, json={
                "filters": [["attachment_links", "is", {"type": "Version", "id": tid}]],
                "fields": ["this_file"], "page": {"size": 50}}).json()["data"]
            rows.append(f"  Attachments minted on the target: {len(att)}")
            for att_row in att:
                made.add("attachments", att_row["id"])
finally:
    os.unlink(path)
    rows.append(f"\ntemp file removed: {not os.path.exists(path)}")

report = "\n".join(rows)
_lib.emit("034_media_round_trip", report, env)
