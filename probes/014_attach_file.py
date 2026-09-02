"""Q: how does an arbitrary file (the ComfyUI workflow JSON) get attached to a Version?"""
import json

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
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
    _lib.register_from(q.json())
    rows.append(f"\nattachments linked to this Version: {len(data)}")
    for x in data[:3]:
        a = x["attributes"]
        rows.append(f"  id={x['id']} name={a.get('this_file', {}).get('name') if isinstance(a.get('this_file'), dict) else a.get('filename')!r} "
                    f"type={a.get('file_extension')!r} size={a.get('file_size')}")
        rows.append(f"    this_file: {json.dumps(a.get('this_file'))[:200]}")
else:
    rows.append(f"\nattachment query -> {q.status_code} {q.text[:250]}")

actual = "\n".join(rows)
_lib.record("014_attach_file", "GET /entity/versions/{id}/_upload (no field) -> PUT -> complete",
            "Arbitrary files attach to a Version as Attachment entities.",
            actual,
            "Same three-step upload as media but with NO field in the path: GET /entity/versions/{id}/_upload "
            "gives upload_type=Attachment, and the file lands as an Attachment entity linked through "
            "attachment_links. Retrieving it needs POST /entity/attachments/_search - a multi-entity field "
            "cannot be filtered by flat filter[] params (400 'invalid/missing entity hash'), it needs an "
            "entity hash {type, id}, and only the _search body can carry one.",
            env, tags=("write", "upload", "attachment", "provenance", "version", "multi-entity", "filter"))
print(actual)
