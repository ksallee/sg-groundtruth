"""Field type `entity` — the single-entity link. Read, write, clear, filter.

Sibling of `multi_entity`: same {type, id} hash, but one slot rather than a list, and — the thing that
bites — a dotted path through it actually reads back (probe 016 says the multi_entity one does not).

Read-only half runs ungated. Writes go into the sandbox project only, behind --write.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
rows = []


def errobj(r):
    """The whole errors[] object, parsed. Never sliced: `source` names the legal vocabulary."""
    try:
        return r.json().get("errors", [r.json()])
    except ValueError:
        return [r.text]


def errs(r):
    return json.dumps(errobj(r), indent=1)


def search(entity, filt, fields=("code",), size=500):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": filt, "fields": list(fields), "page": {"size": size}})
    return (len(r.json()["data"]), None) if r.ok else (f"{r.status_code}", errobj(r))


# ---------------------------------------------------------------- schema
rows.append("=== schema: Version fields whose data_type is 'entity'")
fields = c.get("/schema/Version/fields").json()["data"]


def prop(f, name, default=None):
    p = fields[f].get("properties", {}).get(name)
    return (p or {}).get("value", default) if isinstance(p, dict) else default


ent_fields = sorted(f for f, d in fields.items() if (d.get("data_type") or {}).get("value") == "entity")
rows.append(f"  {len(ent_fields)} of {len(fields)}: {ent_fields}")
for f in ("sg_task", "entity", "user", "created_by"):
    if f in fields:
        rows.append(f"  {f:<12} editable={(fields[f].get('editable') or {}).get('value')} "
                    f"valid_types={prop(f, 'valid_types')}")

# ---------------------------------------------------------------- read
rows.append("\n=== read: where an entity value lands")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                      "fields": "code,entity,sg_task,entity.Shot.code",
                                      "page[size]": 1})
row = r.json()["data"][0]
_lib.note_from(row)
rows.append(json.dumps(row, indent=1))
rows.append(f"  attributes keys: {sorted(row.get('attributes', {}))}")
rows.append(f"  relationships keys: {sorted(row.get('relationships', {}))}")

rows.append("\n  same dotted field on a row whose link IS a Shot (the row above links an Asset):")
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [PROJ, ["entity", "type_is", "Shot"]],
                 "fields": ["code", "entity", "entity.Shot.code"], "page": {"size": 1}})
if r.ok and r.json()["data"]:
    shot_row = r.json()["data"][0]
    _lib.note_from(shot_row)
    rows.append(f"  attributes {json.dumps(shot_row['attributes'])}")
    rows.append(f"  relationships.entity.data {json.dumps(shot_row['relationships']['entity']['data'])}")
else:
    rows.append(f"  {r.status_code} {errs(r)}")

# ---------------------------------------------------------------- operators, from the API itself
rows.append("\n=== operators: a bogus relation makes the API enumerate the legal ones")
_, e = search("versions", [PROJ, ["entity", "definitely_not_an_operator", None]])
rows.append(json.dumps(e, indent=1) if e else "(no error — the bogus operator was accepted?!)")
raw = json.dumps(e)
OPS = re.findall(r'"(\w+)"', re.search(r'Valid relations: \[(.*?)\]', raw).group(1).replace('\\"', '"'))
rows.append(f"  parsed: {OPS}")

# ---------------------------------------------------------------- filter value shapes
shots = c.get("/entity/shots", params={"filter[project.Project.id]": PROJECT, "fields": "code",
                                       "page[size]": 3}).json()["data"]
_lib.note_from(shots)
sids = [s["id"] for s in shots]
scodes = [s["attributes"]["code"] for s in shots]
base, _ = search("versions", [PROJ])
rows.append(f"\n=== filter value shapes on Version.entity (baseline {base} versions in project)")
SHAPES = [
    ("{type,id}", {"type": "Shot", "id": sids[0]}),
    ("[{type,id}x2]", [{"type": "Shot", "id": i} for i in sids[:2]]),
    ("[{id}x2]", [{"id": i} for i in sids[:2]]),
    ("[bare int x2]", sids[:2]),
    ("None", None),
    ("'Shot'", "Shot"),
    (f"name {scodes[0]!r}", scodes[0]),
]
rows.append("  " + "".join(f"{n:<16}" for n, _ in [("operator", 0)] + SHAPES))
for op in OPS or ["is", "is_not", "in", "not_in"]:
    cells = []
    for _, v in SHAPES:
        n, e2 = search("versions", [PROJ, ["entity", op, v]])
        cells.append(str(n) if not e2 else f"{n}")
    rows.append(f"  {op:<16}" + "".join(f"{x:<16}" for x in cells))
rows.append("  (a bare number is a row count; 400 means the shape was rejected)")

rows.append("\n  full error for `in` with [{id}] — no type:")
_, e = search("versions", [PROJ, ["entity", "in", [{"id": sids[0]}]]])
rows.append(json.dumps(e, indent=1))
rows.append("\n  full error for `is` with a bare int:")
_, e = search("versions", [PROJ, ["entity", "is", sids[0]]])
rows.append(json.dumps(e, indent=1) if e else "(accepted)")
rows.append("\n  full error for `in` with bare ints:")
_, e = search("versions", [PROJ, ["entity", "in", sids[:2]]])
rows.append(json.dumps(e, indent=1) if e else "(accepted)")

rows.append("\n=== dotted path through the single link, and negative controls")
for label, filt in [
    (f"entity.Shot.code is {scodes[0]!r}", [["entity.Shot.code", "is", scodes[0]]]),
    ("entity.Shot.code is 'ZZZNOPE'", [["entity.Shot.code", "is", "ZZZNOPE"]]),
    ("entity.Shot.code in [2 real]", [["entity.Shot.code", "in", scodes[:2]]]),
    ("entity.Shot.code contains code[2:-2]", [["entity.Shot.code", "contains", scodes[0][2:-2]]]),
    ("entity is None (unlinked rows)", [["entity", "is", None]]),
    ("entity is {Shot,99999999}", [["entity", "is", {"type": "Shot", "id": 99999999}]]),
]:
    n, e = search("versions", [PROJ] + filt)
    rows.append(f"  {label:<40} -> {n} {(e or '')[:200]}")

# An id is unique per entity TYPE, not per site, so the same integer can name a Shot and an Asset.
# That is what makes a wrong `type` in the hash dangerous rather than merely wrong.
seen = {}
for kind in ("shots", "assets", "tasks", "sequences"):
    d = c.get(f"/entity/{kind}", params={"fields": "id", "page[size]": 250}).json()["data"]
    seen[kind] = {x["id"] for x in d}
rows.append("\n=== is an id unique per type, or site-wide? (first 250 rows of each)")
for kind, ids in seen.items():
    rows.append(f"  {kind:<10} n={len(ids):<4} id range {min(ids)}..{max(ids)}")
COLLIDE = next((i for i in seen["shots"] if i in seen["assets"]), None)
rows.append(f"  shot ids that also name an Asset: {len(seen['shots'] & seen['assets'])} "
            f"-> collision case {COLLIDE}")

# ---------------------------------------------------------------- write / clear
if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the write/clear half)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    rows.append("\n=== write, in the sandbox project only (the sample project is read; never written)")

    def ensure_shot(code):
        f = {"filters": [["project", "is", {"type": "Project", "id": SANDBOX}], ["code", "is", code]],
             "fields": ["code"]}
        r = c.post("/entity/shots/_search", headers=ARR, json=f)
        d = r.json()["data"]
        if d:
            return d[0]["id"]
        return c.post("/entity/shots", headers=JSN,
                      json={"project": {"type": "Project", "id": SANDBOX}, "code": code}).json()["data"]["id"]

    shot_a, shot_b = ensure_shot("zzprobe_entity_a"), ensure_shot("zzprobe_entity_b")
    r = c.post("/entity/tasks", headers=JSN,
               json={"project": {"type": "Project", "id": SANDBOX}, "content": "zzprobe_entity",
                     "entity": {"type": "Shot", "id": shot_a}})
    task = r.json()["data"]["id"] if r.ok else None
    r = c.post("/entity/versions", headers=JSN,
               json={"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_entity"})
    vid = r.json()["data"]["id"]
    other_shot = sids[0]  # a Shot in the READ-ONLY sample project; only the sandbox Version is mutated
    rows.append(f"  created Version {vid}; shots A/B in sandbox, Task {task}; cross-project Shot {other_shot}")

    def upd(body):
        return c.request("PUT", f"/entity/versions/{vid}", headers=JSN, json=body)

    def link(field="entity"):
        d = c.get(f"/entity/versions/{vid}", params={"fields": f"code,{field}"}).json()["data"]
        return (d.get("relationships", {}).get(field) or {}).get("data")

    def attempt(label, body, field="entity", preset=True):
        if preset:
            upd({field: {"type": "Shot", "id": shot_a}})
        r = upd(body)
        after = link(field)
        rows.append(f"\n  {label}\n    -> {r.status_code}; reads back as {json.dumps(after)}")
        if not r.ok:
            rows.append("    " + errs(r).replace("\n", "\n    "))

    attempt("set  entity = {type:Shot, id:A}", {"entity": {"type": "Shot", "id": shot_a}}, preset=False)
    attempt("set  entity = <bare int B>", {"entity": shot_b})
    attempt("set  entity = {id:B}  (no type)", {"entity": {"id": shot_b}})
    attempt("set  entity = {type:Asset, id:<a real SHOT id>}", {"entity": {"type": "Asset", "id": shot_a}})
    attempt("set  entity = {type:Shot, id:99999999}", {"entity": {"type": "Shot", "id": 99999999}})
    attempt("set  entity = a Shot in ANOTHER project", {"entity": {"type": "Shot", "id": other_shot}})
    if COLLIDE:
        attempt(f"set  entity = {{type:Shot,  id:{COLLIDE}}}", {"entity": {"type": "Shot", "id": COLLIDE}})
        attempt(f"set  entity = {{type:Asset, id:{COLLIDE}}}  same id, wrong type",
                {"entity": {"type": "Asset", "id": COLLIDE}})
    attempt("set  sg_task = {type:Task, id:T}", {"sg_task": {"type": "Task", "id": task}}, field="sg_task",
            preset=False)
    attempt("set  sg_task = {type:Shot, id:A}   (outside valid_types)", {"sg_task": {"type": "Shot", "id": shot_a}},
            field="sg_task", preset=False)
    attempt("set  user = {type:Shot, id:A}      (outside valid_types)", {"user": {"type": "Shot", "id": shot_a}},
            field="user", preset=False)
    attempt("set  created_by = {type:Shot,id:A} (non-editable field)",
            {"created_by": {"type": "Shot", "id": shot_a}}, field="created_by", preset=False)

    rows.append("\n=== clear: each starts from entity = {Shot, A}")
    for label, val in [("null", None), ("{}", {}), ('""', ""), ("[]", []),
                       ("{type:Shot, id:null}", {"type": "Shot", "id": None})]:
        attempt(f"clear entity = {label}", {"entity": val})

    upd({"entity": None})
    n, e = search("versions", [["project", "is", {"type": "Project", "id": SANDBOX}],
                               ["entity", "is", None]], size=5)
    rows.append(f"\n  after clearing, `entity is None` in the sandbox matches {n} row(s) "
                f"{json.dumps(e) if e else ''} — the unlinked Version is findable")

actual = "\n".join(rows)
_lib.emit("field_types/entity", actual, env)
