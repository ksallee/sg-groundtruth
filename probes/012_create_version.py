"""Q: what does creating a Version require, and how are entity links written?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
SANDBOX = "comfyui-fpt sandbox"
rows = []

projects = c.get("/entity/projects", params={"fields": "name", "page[size]": 100}).json()
_lib.register_from(projects)
pid = next((p["id"] for p in projects["data"] if p["attributes"]["name"] == SANDBOX), None)
rows.append(f"sandbox project id: {pid}")

vschema = c.get("/schema/Version/fields").json()["data"]
rows.append(f"Version mandatory fields: {sorted(f for f, d in vschema.items() if (d.get('mandatory') or {}).get('value'))}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write)")
else:
    # a parent to hang the Version on — probe 005 says `entity` is the real convention
    shots = c.get("/entity/shots", params={"filter[project.Project.id]": pid, "fields": "code"}).json()
    if shots["data"]:
        shot = shots["data"][0]
    else:
        r = c.post("/entity/shots", json={"project": {"type": "Project", "id": pid}, "code": "sbx_0010"},
                   headers={"Content-Type": "application/json"})
        rows.append(f"POST /entity/shots -> {r.status_code}")
        shot = r.json()["data"] if r.ok else None
        if not r.ok:
            rows.append(json.dumps(r.json(), indent=1)[:400])
    rows.append(f"shot id: {shot['id'] if shot else None}")

    attempts = [
        ("minimal (project + code)", {"project": {"type": "Project", "id": pid}, "code": "probe_v001"}),
        ("with entity link", {"project": {"type": "Project", "id": pid}, "code": "probe_v002",
                              "entity": {"type": "Shot", "id": shot["id"]},
                              "description": "written by probe 012", "sg_status_list": "rev"}),
        ("entity as bare id (no type)", {"project": {"type": "Project", "id": pid}, "code": "probe_v003",
                                         "entity": shot["id"]}),
        ("no project at all", {"code": "probe_v004"}),
    ]
    for label, body in attempts:
        r = c.post("/entity/versions", json=body, headers={"Content-Type": "application/json"})
        note = ""
        if r.ok:
            d = r.json()["data"]
            note = f"id={d['id']} rels={sorted(d.get('relationships', {}))}"
        else:
            note = json.dumps(r.json().get("errors", [{}])[0].get("detail", ""))[:170]
        rows.append(f"  {r.status_code} {label}: {note}")

actual = "\n".join(rows)
_lib.record("012_create_version", "POST /api/v1/entity/versions",
            "Versions need a project; entity links are written as {type, id}.",
            actual, "see below", env, tags=("write", "version", "create", "entity-field"))
print(actual)
