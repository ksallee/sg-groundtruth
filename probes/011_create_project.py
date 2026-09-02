"""Q: what does creating a Project over REST require, and does it work from a script user?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
SANDBOX = "comfyui-fpt sandbox"
rows = []

schema = c.get("/schema/Project/fields").json()["data"]
mandatory = sorted(f for f, d in schema.items() if (d.get("mandatory") or {}).get("value"))
editable = sorted(f for f, d in schema.items() if (d.get("editable") or {}).get("value"))
rows.append(f"Project fields: {len(schema)}")
rows.append(f"mandatory: {mandatory}")
rows.append(f"editable (first 25): {editable[:25]}")

existing = c.get("/entity/projects", params={"fields": "name", "page[size]": 100}).json()
_lib.register_from(existing)
hit = [p for p in existing["data"] if p["attributes"]["name"] == SANDBOX]
rows.append(f"\nsandbox already present: {bool(hit)}")

if hit:
    rows.append(f"reusing project id {hit[0]['id']}")
elif _lib.writes_allowed():
    r = c.post("/entity/projects", json={"name": SANDBOX},
               headers={"Content-Type": "application/json"})
    rows.append(f"\nPOST /entity/projects -> {r.status_code}")
    if r.ok:
        d = r.json()["data"]
        rows.append(f"created id={d['id']}; attributes returned: {sorted(d.get('attributes', {}))[:12]}")
    else:
        rows.append(json.dumps(r.json(), indent=1)[:600])
else:
    rows.append("\n(read-only run; pass --write to create)")

actual = "\n".join(rows)
_lib.record("011_create_project", "POST /api/v1/entity/projects",
            "Projects can be created over REST by a script user.",
            actual, "see below", env, tags=("write", "project", "create", "sandbox"))
print(actual)
