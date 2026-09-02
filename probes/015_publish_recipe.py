"""Q: what is the complete publish sequence a node performs, start to finish?"""
import json

import requests

import _lib

env = _lib.load_env()
c = _lib.client()

# Read-only by default (CLAUDE.md). This probe creates a Version and uploads media.
if not _lib.writes_allowed():
    raise SystemExit("015_publish_recipe writes to the site; re-run with --write")
SANDBOX = _lib.sandbox_name(env)

projects = c.get("/entity/projects", params={"fields": "name", "page[size]": 100}).json()
_lib.note_from(projects)
pid = next(p["id"] for p in projects["data"] if p["attributes"]["name"] == SANDBOX)
shot = c.get("/entity/shots", params={"filter[project.Project.id]": pid, "fields": "code"}).json()["data"][0]

PNG = bytes.fromhex("89504e470d0a1a0a0000000d494844520000001000000010080200000090916836"
                    "0000001f49444154789c63fcffff3f0326c8281a0d34d047230d34d0400333d400"
                    "00b4a80f0e6f2b2e4e0000000049454e44ae426082")
WORKFLOW = {"nodes": [{"id": 1, "type": "KSampler", "widgets_values": [12345, "euler", 20, 7.5]}]}
PROVENANCE = {"model": "flux1-dev.safetensors", "seed": 12345, "sampler": "euler", "steps": 20, "cfg": 7.5}

steps = []


def upload(vid, field, filename, payload):
    path = f"/entity/versions/{vid}/_upload" if not field else f"/entity/versions/{vid}/{field}/_upload"
    b = c.get(path, params={"filename": filename}).json()
    requests.put(b["links"]["upload"], data=payload, timeout=60)
    r = c.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}},
               headers={"Content-Type": "application/json"})
    return r.status_code


r = c.post("/entity/versions", headers={"Content-Type": "application/json"}, json={
    "project": {"type": "Project", "id": pid},
    "entity": {"type": "Shot", "id": shot["id"]},
    "code": "publish_v001",
    "sg_status_list": "rev",
    "description": json.dumps(PROVENANCE),
})
vid = r.json()["data"]["id"]
steps.append(f"1. POST /entity/versions -> {r.status_code}, id={vid}")
steps.append(f"2. upload image     -> {upload(vid, 'image', 'render.png', PNG)}")
steps.append(f"3. upload media     -> {upload(vid, 'sg_uploaded_movie', 'render.png', PNG)}")
steps.append(f"4. attach workflow  -> {upload(vid, None, 'workflow.json', json.dumps(WORKFLOW).encode())}")

back = c.get(f"/entity/versions/{vid}",
             params={"fields": "code,description,sg_status_list,entity,image,sg_uploaded_movie"}).json()
_lib.note_from(back)
steps.append(f"5. read back        -> {back['data']['attributes'].get('code')}, "
             f"status={back['data']['attributes'].get('sg_status_list')}, "
             f"entity={json.dumps(back['data']['relationships'].get('entity', {}).get('data'))}")

call = '''# get/post are FPT.get/.post from src/sg_groundtruth/client.py — they add auth and the /api/v1 prefix.
JSON = {"Content-Type": "application/json"}
provenance = {"model": "flux1-dev.safetensors", "seed": 12345, "sampler": "euler", "steps": 20, "cfg": 7.5}
workflow_json = json.dumps(workflow_graph).encode()

# 1. create the Version, provenance as JSON in description
r = post("/entity/versions", headers=JSON, json={
    "project": {"type": "Project", "id": PROJECT_ID},
    "entity":  {"type": "Shot",    "id": SHOT_ID},     # entity links are {type, id}; bare ids 400
    "code": "publish_v001",
    "sg_status_list": "rev",
    "description": json.dumps(provenance),
})
version_id = r.json()["data"]["id"]

# 2-4. one three-step upload per file. No field in the path = generic Attachment.
for field, filename, payload in [("image", "render.png", png),
                                 ("sg_uploaded_movie", "render.png", png),
                                 (None, "workflow.json", workflow_json)]:
    path = f"/entity/versions/{version_id}/_upload" if field is None \\
        else f"/entity/versions/{version_id}/{field}/_upload"
    b = get(path, params={"filename": filename}).json()
    requests.put(b["links"]["upload"], data=payload)                    # presigned S3
    post(b["links"]["complete_upload"], headers=JSON,                   # upload_data required, even empty
         json={"upload_info": b["data"], "upload_data": {}})'''

report = "\n".join([
    "=== sequence",
    *steps,
    "",
    "=== the call",
    call,
    "",
    "=== gotchas",
    "- `project` is not schema-mandatory on Version but omitting it returns 400 (probe 012).",
    "- `upload_data` must be present in the complete call even though it is empty (probe 013).",
    "- The thumbnail transcodes asynchronously — reading `image` straight back gives a placeholder "
    "under /images/status/transient/ (probe 013).",
    "- To find the attachments again use POST /entity/attachments/_search with "
    "Content-Type: application/vnd+shotgun.api3_array+json and an entity hash filter (probe 014).",
])
_lib.emit("001_publish_version_with_media", report, env)
