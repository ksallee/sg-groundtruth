"""Q: which writes move a record's `updated_at`: a finished upload, a link added from the other side,
a write that changes nothing?

An offline client that syncs with `[["updated_at", "greater_than", T]]` misses every change that does
not move the stamp. Each step below makes one change and reads `updated_at` and `updated_by` on the
record before and after. Steps are three seconds apart, since the stamp is returned to the second.

Writes only: throwaway rows `zzprobe_124_*` in the sandbox, deleted before exit.

    python probes/124_updated_at_bumps.py --write
"""
import json
import subprocess
import tempfile
import time
from pathlib import Path

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
if not _lib.writes_allowed():
    raise SystemExit("124_updated_at_bumps writes to the site; re-run with --write")
rows = []
SB = _lib.sandbox_id(c, env)
PROJ = {"type": "Project", "id": SB}
tmp = Path(tempfile.mkdtemp(prefix="zzprobe_124_"))
JPG = tmp / "zzprobe_124.jpg"
subprocess.run(["magick", "-size", "640x360", "gradient:red-blue", str(JPG)], check=True)


def stamp(slug, rid):
    d = c.get(f"/entity/{slug}/{rid}", params={"fields": "updated_at,updated_by"}).json()["data"]
    return d["attributes"]["updated_at"], (d["relationships"]["updated_by"]["data"] or {}).get("type")


def step(label, slug, rid, action):
    before = stamp(slug, rid)
    time.sleep(3)
    res = action()
    time.sleep(2)
    after = stamp(slug, rid)
    rows.append(f"  {label:<62} {res!s:<6} updated_at {'MOVED' if after[0] != before[0] else 'same '}"
                f"  {before[0]} -> {after[0]}")
    return after


def upload(path):
    i = c.get(f"{path}/_upload", params={"filename": JPG.name}).json()
    requests.put(i["links"]["upload"], data=JPG.read_bytes(), timeout=120)
    return c.post(i["links"]["complete_upload"], json={"upload_info": i["data"], "upload_data": {}}).status_code


def wait_image(slug, rid):
    for _ in range(30):
        v = c.get(f"/entity/{slug}/{rid}", params={"fields": "image"}).json()["data"]["attributes"]["image"]
        if v and "/images/status/transient/" not in v:
            return True
        time.sleep(5)
    return False


with _lib.Created(c) as made:
    def new(slug, **body):
        r = c.post(f"/entity/{slug}", json={"project": PROJ, **body})
        assert r.status_code == 201, r.text
        return made.add(slug, r.json()["data"]["id"])

    slate = new("slates", code="zzprobe_124_slate")
    scene = new("scenes", code="zzprobe_124_scene")
    shot = new("shots", code="zzprobe_124_sh")
    rows.append("===== on a Slate")
    step("PUT description (control)", "slates", slate,
         lambda: c.put(f"/entity/slates/{slate}", json={"description": "a"}).status_code)
    step("PUT description, the same value again", "slates", slate,
         lambda: c.put(f"/entity/slates/{slate}", json={"description": "a"}).status_code)
    step("image: the three upload calls, read straight after complete", "slates", slate,
         lambda: upload(f"/entity/slates/{slate}/image"))
    before = stamp("slates", slate)
    done = wait_image("slates", slate)
    after = stamp("slates", slate)
    rows.append(f"  {'image: the transcode finishing (placeholder replaced)':<62} {done!s:<6} updated_at "
                f"{'MOVED' if after[0] != before[0] else 'same '}  {before[0]} -> {after[0]}")
    holder = {}

    def version_on_slate():
        holder["v"] = new("versions", code="zzprobe_124_v", entity={"type": "Slate", "id": slate})
        return 201
    step("a Version created with entity=Slate (Slate.sg_versions reverse)", "slates", slate,
         version_on_slate)
    held = c.get(f"/entity/slates/{slate}", params={"fields": "sg_versions"}).json()["data"]
    rows.append(f"    Slate.sg_versions now holds {len(held['relationships']['sg_versions']['data'] or [])}")
    step("a Note created with note_links=[Slate] (Slate.notes reverse)", "slates", slate,
         lambda: made.add("notes", c.post("/entity/notes", json={
             "project": PROJ, "subject": "zzprobe_124", "content": "zzprobe_124",
             "note_links": [{"type": "Slate", "id": slate}]}).json()["data"]["id"]) and 201)
    step("that Version's entity cleared (the reverse link removed)", "slates", slate,
         lambda: c.put(f"/entity/versions/{holder['v']}", json={"entity": None}).status_code)

    rows.append("\n===== on a Scene, through the stock pair Shot.sg_scene / Scene.shots")
    step("PUT Shot.sg_scene = the Scene", "scenes", scene,
         lambda: c.put(f"/entity/shots/{shot}", json={"sg_scene": {"type": "Scene", "id": scene}}).status_code)
    step("PUT Shot.sg_scene = null", "scenes", scene,
         lambda: c.put(f"/entity/shots/{shot}", json={"sg_scene": None}).status_code)
    step("PUT Scene.shots = [the Shot]: and the Shot's own stamp below", "scenes", scene,
         lambda: c.put(f"/entity/scenes/{scene}", json={"shots": [{"type": "Shot", "id": shot}]}).status_code)
    step("the Shot, after Scene.shots named it (re-read only)", "shots", shot, lambda: "read")

    rows.append("\n===== on a Version, sg_uploaded_movie")
    v = holder["v"]
    step("sg_uploaded_movie: the three calls", "versions", v,
         lambda: upload(f"/entity/versions/{v}/sg_uploaded_movie"))
    before = stamp("versions", v)
    done = wait_image("versions", v)
    time.sleep(20)
    after = stamp("versions", v)
    rows.append(f"  {'the transcode finishing, +20s':<62} {done!s:<6} updated_at "
                f"{'MOVED' if after[0] != before[0] else 'same '}  {before[0]} -> {after[0]}")

    rows.append("\n===== the cursor itself")
    t = before[0]
    q = c.post("/entity/versions/_search", headers=ARR, json={
        "filters": [["updated_at", "greater_than", t], ["project", "is", PROJ]],
        "fields": ["updated_at"], "page": {"size": 50}}).json()
    rows.append(f"  updated_at greater_than {t}: {len(q.get('data', []))} rows "
                f"{'' if 'data' in q else json.dumps(q.get('errors'))}")

    _lib.emit("124_updated_at_bumps", "\n".join(rows), env)
    # the uploads made Attachments behind image and sg_uploaded_movie, and the server's transcodes of
    # the movie are Attachments named <hash>_zzprobe_124*; all go after the rows
    att = c.post("/entity/attachments/_search", headers=ARR, json={
        "filters": [["filename", "contains", "zzprobe_124"]], "fields": ["id"],
        "page": {"size": 50}}).json().get("data", [])
    for a in att:
        made.rows.insert(0, ("attachments", a["id"]))
