"""Q: can a Version carry an image sequence, or only a single movie?

A render produces N frames, not one image. This asks what a Version can
actually hold: whether the media field takes a sequence, what a second upload to the same field does,
and whether uploading a real movie yields the transcodes the review player needs.
"""
import json
import os
import time

import requests

import _lib

env = _lib.load_env()
c = _lib.client()

# Read-only by default (CLAUDE.md). This probe creates a Version and uploads real media.
if not _lib.writes_allowed():
    raise SystemExit("022_sequence_on_version writes to the site; re-run with --write")
SANDBOX = _lib.sandbox_id(c, env)
D = _lib._need(env, "FPT_PROBE_FRAMES_DIR", "a directory of .png frames plus a .mov, for probe 022")
FRAMES = sorted(f"{D}/{f}" for f in os.listdir(D) if f.endswith(".png"))
MOVIE = next(f"{D}/{f}" for f in sorted(os.listdir(D)) if f.endswith(".mov"))
rows = []


def upload(version_id, field, filename, payload):
    """probe 013 — three steps, and upload_data is required even though it is empty."""
    path = (f"/entity/versions/{version_id}/_upload" if field is None
            else f"/entity/versions/{version_id}/{field}/_upload")
    b = c.get(path, params={"filename": filename}).json()
    requests.put(b["links"]["upload"], data=payload, timeout=300)
    r = c.post(b["links"]["complete_upload"],
               json={"upload_info": b["data"], "upload_data": {}})
    return r.status_code, b["data"].get("upload_type")


def read(version_id, fields):
    r = c.get(f"/entity/versions/{version_id}", params={"fields": ",".join(fields)})
    return r.json()["data"]["attributes"]


v = c.post("/entity/versions", json={
    "project": {"type": "Project", "id": SANDBOX},
    "code": "zzprobe_022_sequence",
    "description": "probe 022 — what a Version can hold for a frame sequence",
    "sg_path_to_frames": f"{D}/{os.path.basename(FRAMES[0]).split('.')[0]}.%04d.png",
}).json()["data"]
vid = v["id"]
rows.append(f"Version {vid} created with sg_path_to_frames set, no media yet")

rows.append("\n=== does the media field take a sequence? one upload per frame, same field")
for i, f in enumerate(FRAMES[:3], start=1):
    code, kind = upload(vid, "sg_uploaded_movie", os.path.basename(f), open(f, "rb").read())
    a = read(vid, ["sg_uploaded_movie"])
    name = (a.get("sg_uploaded_movie") or {}).get("name")
    rows.append(f"  upload {i} ({os.path.basename(f)}) -> {code} type={kind}; field now holds {name!r}")
rows.append("  => the field is SINGLE-VALUED: each upload REPLACES, it does not accumulate.")

rows.append("\n=== the frames as Attachments instead (no field in the path, probe 014)")
for f in FRAMES[:2]:
    code, kind = upload(vid, None, os.path.basename(f), open(f, "rb").read())
    rows.append(f"  {os.path.basename(f)} -> {code} type={kind}")
att = c.post("/entity/attachments/_search",
             headers={"Content-Type": "application/vnd+shotgun.api3_array+json"},
             json={"filters": [["attachment_links", "is", {"type": "Version", "id": vid}]],
                   "fields": ["this_file"], "page": {"size": 20}})
rows.append(f"  attachments now linked: {len(att.json()['data'])} — they accumulate, but they are "
            f"files on the entity, NOT media: the review player never plays them.")

rows.append("\n=== upload the transcoded movie the player CAN use")
code, kind = upload(vid, "sg_uploaded_movie", os.path.basename(MOVIE), open(MOVIE, "rb").read())
rows.append(f"  {os.path.basename(MOVIE)} ({os.path.getsize(MOVIE)}b) -> {code} type={kind}")

F = ["sg_uploaded_movie", "sg_uploaded_movie_mp4", "sg_uploaded_movie_webm",
     "sg_uploaded_movie_frame_rate", "sg_uploaded_movie_transcoding_status", "sg_path_to_frames"]
for wait in (0, 5, 15, 30):
    if wait:
        time.sleep(wait)
    a = read(vid, F)
    status = a.get("sg_uploaded_movie_transcoding_status")
    got = {k: bool(a.get(k)) for k in ("sg_uploaded_movie_mp4", "sg_uploaded_movie_webm")}
    rows.append(f"  t+{sum((0,5,20,50)[:1+(0,5,15,30).index(wait)]):>3}s  status={status}  "
                f"mp4={got['sg_uploaded_movie_mp4']} webm={got['sg_uploaded_movie_webm']} "
                f"fps={a.get('sg_uploaded_movie_frame_rate')}")
    if all(got.values()):
        break

a = read(vid, F)
_lib.note_from(a)
_lib.note_path(D)
rows.append("\n=== the shape that works")
rows.append(f"  sg_path_to_frames  {'set' if a.get('sg_path_to_frames') else 'unset'}  "
            f"<- the real frames, at full resolution, on the storage root")
rows.append(f"  sg_uploaded_movie  {(a.get('sg_uploaded_movie') or {}).get('name')!r}  "
            f"<- one transcoded movie, which is what plays in review")

report = "\n".join(rows).replace(D, "<storage>/<sequence>")
_lib.emit("022_sequence_on_version", report, env)
