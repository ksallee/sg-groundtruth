"""Q: how does an arbitrary file get attached to a Version?"""
import json

import requests

import _lib

env = _lib.load_env()
c = _lib.client()

# Read-only by default (CLAUDE.md). This probe uploads a real file.
if not _lib.writes_allowed():
    raise SystemExit("014_attach_file writes to the site; re-run with --write")
VERSION_ID = 26263
rows = []

WORKFLOW = json.dumps({"probe": "014", "nodes": [{"id": 1, "type": "KSampler", "seed": 12345}]}).encode()

r = c.get(f"/entity/versions/{VERSION_ID}/_upload", params={"filename": "workflow.json"})
rows.append(f"1. init (no field in path) -> {r.status_code}, upload_type={r.json()['data'].get('upload_type')}")
b = r.json()

put = requests.put(b["links"]["upload"], data=WORKFLOW, timeout=60)
rows.append(f"2. PUT {len(WORKFLOW)}b -> {put.status_code}")

cr = c.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}},
            headers={"Content-Type": "application/vnd+shotgun.api3_array+json"})
rows.append(f"3. complete -> {cr.status_code} {'' if cr.ok else cr.text[:200]}")

# where did it land?
af = sorted(c.get("/schema/Attachment/fields").json()["data"])
rows.append(f"\nAttachment fields: {af}")
# multi-entity fields cannot be filtered through flat filter[] params — they need an entity hash,
# which only the _search body form can carry.
bad = c.get("/entity/attachments", params={"filter[attachment_links]": f"Version,{VERSION_ID}",
                                           "fields": "filename", "page[size]": 1})
rows.append(f"\nflat filter[] on a multi-entity field -> {bad.status_code} "
            f"{json.dumps(bad.json().get('errors', [{}])[0].get('title'))}")

q = c.post("/entity/attachments/_search", json={
    "filters": [["attachment_links", "is", {"type": "Version", "id": VERSION_ID}]],
    "fields": af, "sort": "-id", "page": {"size": 5}},
    headers={"Content-Type": "application/vnd+shotgun.api3_array+json"})
if q.ok:
    data = q.json()["data"]
    _lib.note_from(q.json())
    rows.append(f"\nattachments linked to this Version: {len(data)}")
    for x in data[:3]:
        a = x["attributes"]
        rows.append(f"  id={x['id']} name={a.get('this_file', {}).get('name') if isinstance(a.get('this_file'), dict) else a.get('filename')!r} "
                    f"type={a.get('file_extension')!r} size={a.get('file_size')}")
        rows.append(f"    this_file: {json.dumps(a.get('this_file'))[:200]}")
else:
    rows.append(f"\nattachment query -> {q.status_code} {q.text[:250]}")

actual = "\n".join(rows)
_lib.emit("014_attach_file", actual, env)
