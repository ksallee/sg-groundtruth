"""Q: is the middle segment of a dotted field path validated, and against what?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
HASH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
rows = []

schema = c.get("/schema/Version/fields").json()["data"]
for f in ("entity", "sg_task"):
    rows.append(f"Version.{f} valid_types: {json.dumps(schema[f]['properties']['valid_types']['value'])}")

# A Version that links a Shot, so `entity.Shot.code` is the control that must return a value.
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [PROJ, ["entity", "type_is", "Shot"]],
                 "fields": ["code", "entity"], "page": {"size": 1}})
_lib.note_from(r.json())
row = r.json()["data"][0]
VID, LINKED = row["id"], row["relationships"]["entity"]["data"]
rows.append(f"control Version links {LINKED['type']} {LINKED['name']!r}")

PATHS = [
    ("entity.Shot.code", "valid_types member, the row's own type"),
    ("entity.Asset.code", "valid_types member, not the row's type"),
    ("entity.Sequence.code", "valid_types member, not the row's type"),
    ("entity.Task.content", "real type, real field, outside valid_types"),
    ("entity.Bogus.code", "type does not exist"),
    ("entity.Shot.bogusfield", "field does not exist on Shot"),
    ("sg_task.Task.content", "valid_types member of the other field"),
    ("sg_task.Shot.code", "real type, outside sg_task valid_types"),
]


def outcome(r, path):
    if not r.ok:
        return f"{r.status_code} {_lib.scrub(r.text.strip(), env)}"
    data = r.json()["data"]
    if not data:
        return f"{r.status_code} 0 rows"
    a = data[0].get("attributes", {})
    if path not in a:
        return f"{r.status_code} key absent, attributes {sorted(a)}"
    return f"{r.status_code} {json.dumps(a[path])}"


rows.append("\n=== READ: the path in the projection, one Version, three parsers")
for path, why in PATHS:
    s = c.post("/entity/versions/_search", headers=ARR,
               json={"filters": [["id", "is", VID]], "fields": ["code", path]})
    h = c.post("/entity/versions/_search", headers=HASH,
               json={"filters": {"logical_operator": "and", "conditions": [["id", "is", VID]]},
                     "fields": ["code", path]})
    g = c.get("/entity/versions", params={"filter[id]": VID, "fields": f"code,{path}"})
    rows.append(f"  {path}  ({why})")
    rows.append(f"    _search api3_array -> {outcome(s, path)}")
    rows.append(f"    _search api3_hash  -> {outcome(h, path)}")
    rows.append(f"    GET ?fields        -> {outcome(g, path)}")


def count(filt):
    r = c.post("/entity/versions/_search", headers=ARR,
               json={"filters": [PROJ, filt], "fields": ["code"], "page": {"size": 200}})
    if not r.ok:
        return f"{r.status_code} {_lib.scrub(r.text.strip(), env)}"
    return f"200 {len(r.json()['data'])} rows"


base = c.post("/entity/versions/_search", headers=ARR,
              json={"filters": [PROJ], "fields": ["code"], "page": {"size": 200}})
rows.append(f"\n=== FILTER: the same paths on the left of a condition, baseline "
            f"{len(base.json()['data'])} Versions")
rows.append(f"  entity.Shot.code is <the control's own code> -> "
            f"{count(['entity.Shot.code', 'is', LINKED['name']])}   (positive control)")
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [PROJ, ["sg_task", "is_not", None]],
                 "fields": ["sg_task.Task.content"], "page": {"size": 1}})
_lib.note_from(r.json())
linked_task = (r.json()["data"] or [{}])[0].get("attributes", {}).get("sg_task.Task.content")
rows.append(f"  sg_task.Task.content is <a linked Task's content> -> "
            f"{count(['sg_task.Task.content', 'is', linked_task]) if linked_task else 'no Version links sg_task here'}"
            f"   (positive control)")
for path, why in PATHS:
    rows.append(f"  {path} is 'ZZZNOPE' -> {count([path, 'is', 'ZZZNOPE'])}")

actual = "\n".join(rows)
_lib.emit("059_dotted_path_type_check", actual, env)
