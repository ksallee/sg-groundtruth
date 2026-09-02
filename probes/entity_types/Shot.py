"""Q: how is a Shot addressed, identified, created and linked?

Shot sits between Sequence and Task and is what most Versions hang off (probe 005), so its slug, its
identity field and its real create contract are on the path of every client that writes shot work.
Probe 012 found the schema's `mandatory` flags are not the create contract; re-establish it here rather
than assume it transfers.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
READ = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSON = {"Content-Type": "application/json"}
TAG = f"zzprobe_shot_{os.getpid()}"
rows = []


def whole_error(r):
    """The entire errors[] object, `source` included. Truncating it throws away the vocabulary the API
    hands you for free (probe 017)."""
    try:
        body = r.json()
    except ValueError:
        return r.text
    return json.dumps(body.get("errors", body), indent=1)


def top(d, k):
    return (d.get(k) or {}).get("value")


def prop(d, k):
    return (d.get("properties", {}).get(k) or {}).get("value")


def search(slug, filters, fields, size=200):
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": filters, "fields": fields, "page": {"size": size}})
    return r


# ---------------------------------------------------------------- slug, verified by calling it
rows.append("=== SLUG: which path answers")
for path in ("/entity/shots", "/entity/shot", "/entity/Shot", "/entity/Shots", "/entity/shotz"):
    r = c.get(path, params={"page[size]": 1, "fields": "code"})
    note = ""
    if r.ok:
        d = r.json()["data"]
        note = (f"  type={d[0]['type']!r} self={d[0]['links']['self']}" if d else "  no rows")
    else:
        note = "  " + json.dumps(r.json().get("errors", [{}])[0].get("detail"))[:110]
    rows.append(f"  GET {path:<16} -> {r.status_code}{note}")
r = c.get("/entity/shots", params={"page[size]": 1, "fields": "code"})
one = r.json()["data"][0] if r.json()["data"] else None
if one:
    _lib.note_from(one)
    rows.append(f"  row type={one['type']!r} links.self={one['links']['self']}")
    rr = c.get(one["links"]["self"], params={"fields": "code"})
    rows.append(f"  GET links.self -> {rr.status_code}")

# ---------------------------------------------------------------- scope
rows.append("\n=== SCOPE: project-scoped or site-wide")
sch = c.get("/schema/Shot/fields").json()["data"]
p = sch["project"]
rows.append(f"  Shot.project data_type={top(p, 'data_type')!r} editable={top(p, 'editable')} "
            f"mandatory={top(p, 'mandatory')} valid_types={prop(p, 'valid_types')}")
for lbl, filt in (("unfiltered", []),
                  ("project is_not <read project>",
                   [["project", "is_not", {"type": "Project", "id": READ}]])):
    r = search("shots", filt, ["code", "project"], size=500)
    if r.ok:
        pids = {}
        for x in r.json()["data"]:
            d = (x.get("relationships", {}).get("project") or {}).get("data") or {}
            pids[d.get("id")] = pids.get(d.get("id"), 0) + 1
        rows.append(f"  _search {lbl:<32} -> {len(r.json()['data'])} rows across "
                    f"{len(pids)} distinct project ids")
    else:
        rows.append(f"  _search {lbl} -> {r.status_code} {whole_error(r)}")
r = search("shots", [["project", "is", {"type": "Project", "id": READ}]], ["code"], size=500)
rows.append(f"  filter project is <read project> -> {len(r.json()['data']) if r.ok else r.status_code}")
r = c.get("/entity/shots", params={"filter[project.Project.id]": READ, "fields": "code", "page[size]": 500})
rows.append(f"  GET filter[project.Project.id]=<read project> -> "
            f"{len(r.json()['data']) if r.ok else r.status_code}")

# ---------------------------------------------------------------- identity
rows.append("\n=== IDENTITY: which field is the name")
for f in ("code", "name", "content", "description", "sg_shot_code"):
    d = sch.get(f)
    rows.append(f"  {f:<14} {'absent from /schema/Shot/fields' if d is None else ''}"
                + ("" if d is None else
                   f"data_type={top(d, 'data_type')!r} mandatory={top(d, 'mandatory')} "
                   f"unique={top(d, 'unique')} display={top(d, 'name')!r}"))
r = c.get("/entity/shots", params={"page[size]": 3, "fields": "code"})
if r.ok:
    _lib.note_from(r.json())
    rows.append("  a row: " + json.dumps([{"id": x["id"], **x["attributes"]} for x in r.json()["data"]]))
r = c.get("/entity/shots", params={"page[size]": 1, "fields": "name"})
rows.append(f"  ?fields=name -> {r.status_code} attributes="
            f"{json.dumps(r.json()['data'][0]['attributes']) if r.ok and r.json()['data'] else '-'}")

# ---------------------------------------------------------------- link census
rows.append("\n=== LINKS: entity and multi_entity fields")
links = [(n, top(d, "data_type"), top(d, "editable"), prop(d, "valid_types"))
         for n, d in sorted(sch.items()) if top(d, "data_type") in ("entity", "multi_entity")]
rows.append(f"  {len(sch)} fields on Shot; {sum(1 for x in links if x[1] == 'entity')} entity, "
            f"{sum(1 for x in links if x[1] == 'multi_entity')} multi_entity")
for n, dt, ed, vt in links:
    v = vt if vt is None or len(vt) <= 6 else f"[{len(vt)} types]"
    rows.append(f"  {dt:<12} {n:<34} editable={str(ed):<5} valid_types={v}")

rows.append("\n=== LINKS: which are actually populated, on the read project")
names = [n for n, dt, ed, vt in links if n not in ("image_source_entity",)]
r = search("shots", [["project", "is", {"type": "Project", "id": READ}]], ["code"] + names, size=200)
if r.ok:
    data = r.json()["data"]
    filled = {}
    for x in data:
        for n in names:
            v = (x.get("relationships", {}).get(n) or {}).get("data")
            if v:
                filled[n] = filled.get(n, 0) + 1
    rows.append(f"  over {len(data)} shots: "
                + json.dumps(dict(sorted(filled.items(), key=lambda kv: -kv[1]))))
    rows.append(f"  never populated: {sorted(n for n in names if n not in filled)}")
    ex = next((x for x in data if (x.get("relationships", {}).get("sg_sequence") or {}).get("data")), None)
    if ex:
        _lib.note_from(ex)
        rows.append("  sg_sequence shape: "
                    + json.dumps(ex["relationships"]["sg_sequence"]["data"]))
else:
    rows.append(f"  {r.status_code} {whole_error(r)}")

# inbound: what points AT a Shot rather than out of it
rows.append("  inbound, over one 500-row page of the read project:")
for slug, ent in (("versions", "Version"), ("tasks", "Task")):
    base = [["project", "is", {"type": "Project", "id": READ}]]
    a = search(slug, base, ["id"], size=500)
    b = search(slug, base + [["entity", "type_is", "Shot"]], ["id"], size=500)
    n = len(a.json()["data"]) if a.ok else a.status_code
    m = len(b.json()["data"]) if b.ok else b.status_code
    rows.append(f"    {ent}.entity type_is Shot -> {m} of {n}")
sh = search("shots", [["project", "is", {"type": "Project", "id": READ}]], ["code"], size=1)
if sh.ok and sh.json()["data"]:
    one_id = sh.json()["data"][0]["id"]
    for slug, ent, path in (("versions", "Version", "entity.Shot.code"),
                            ("tasks", "Task", "entity.Shot.code")):
        r2 = search(slug, [["entity", "is", {"type": "Shot", "id": one_id}]], ["id"], size=200)
        rows.append(f"    {ent} entity is {{Shot,<id>}} -> "
                    f"{len(r2.json()['data']) if r2.ok else whole_error(r2)}")

# ---------------------------------------------------------------- status
rows.append("\n=== STATUS")
for f in ("sg_status_list", "sg_latest_vendor_status"):
    site = c.get(f"/schema/Shot/fields/{f}").json()["data"]
    proj = c.get(f"/schema/Shot/fields/{f}", params={"project_id": READ}).json()["data"]
    valid = prop(proj, "valid_values") or []
    hidden = prop(proj, "hidden_values") or []
    rows.append(f"  Shot.{f}  data_type={top(site, 'data_type')!r} editable={top(site, 'editable')} "
                f"default={prop(site, 'default_value')!r}")
    rows.append(f"    valid_values  {valid}")
    rows.append(f"    hidden_values site={prop(site, 'hidden_values')} read-project={hidden}")
    rows.append(f"    usable        {[v for v in valid if v not in hidden]}")
    rows.append(f"    display_values {json.dumps(prop(proj, 'display_values'))}")
r = search("shots", [["project", "is", {"type": "Project", "id": READ}]], ["code", "sg_status_list"], 500)
if r.ok:
    seen = {}
    for x in r.json()["data"]:
        v = x["attributes"].get("sg_status_list")
        seen[v] = seen.get(v, 0) + 1
    rows.append(f"  distinct sg_status_list over {len(r.json()['data'])} shots: "
                + json.dumps(dict(sorted(seen.items(), key=lambda kv: -kv[1]))))

# ---------------------------------------------------------------- read only / server managed
rows.append("\n=== READ ONLY / SERVER MANAGED")
ro = sorted(n for n, d in sch.items() if not top(d, "editable"))
pivots = [n for n in ro if n.startswith("step_")]
rows.append(f"  editable=false: {len(ro)} fields, {len(pivots)} of them step_<n> pivot_column")
rows.append(f"  non-pivot: {[n for n in ro if not n.startswith('step_')]}")
r = c.get("/entity/shots", params={"page[size]": 5, "fields": ",".join(["code"] + pivots[:6])})
if r.ok and r.json()["data"]:
    vals = {n: sorted({json.dumps(x["attributes"].get(n)) for x in r.json()["data"]})
            for n in pivots[:6]}
    rows.append(f"  {len(pivots)} pivot fields on 5 shots, distinct values: {json.dumps(vals)}")

# ---------------------------------------------------------------- create contract (sandbox only)
if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the create contract)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    rows.append("\n=== CREATE CONTRACT, sandbox project only")
    with _lib.Created(c) as made:
        attempts = [
            ("neither", {}),
            ("code alone", {"code": f"{TAG}_a"}),
            ("project alone", {"project": {"type": "Project", "id": SANDBOX}}),
            ("both", {"project": {"type": "Project", "id": SANDBOX}, "code": f"{TAG}_b"}),
            ("both, code repeated in the same project",
             {"project": {"type": "Project", "id": SANDBOX}, "code": f"{TAG}_b"}),
            ("both, code empty string", {"project": {"type": "Project", "id": SANDBOX}, "code": ""}),
            ("both, project as a bare id", {"project": SANDBOX, "code": f"{TAG}_c"}),
            ("both plus sg_status_list and sg_sequence",
             {"project": {"type": "Project", "id": SANDBOX}, "code": f"{TAG}_d",
              "sg_status_list": "ip", "description": "written by entity_types/Shot"}),
        ]
        for label, body in attempts:
            r = c.post("/entity/shots", headers=JSON, json=body)
            if r.ok:
                d = r.json()["data"]
                made.add("shots", d["id"])
                rows.append(f"  {r.status_code} {label:<42} id set, code="
                            f"{d['attributes'].get('code')!r} "
                            f"status={d['attributes'].get('sg_status_list')!r} "
                            f"rels={sorted(d.get('relationships', {}))[:6]}")
            else:
                rows.append(f"  {r.status_code} {label:<42} {whole_error(r)}")

        # what a create with no status yields, and what the server filled in
        r = c.post("/entity/shots", headers=JSON,
                   json={"project": {"type": "Project", "id": SANDBOX}, "code": f"{TAG}_e"})
        if r.ok:
            sid = made.add("shots", r.json()["data"]["id"])
            back = c.get(f"/entity/shots/{sid}")
            a = back.json()["data"]["attributes"]
            rows.append("  server-filled on a bare create: "
                        + json.dumps({k: a.get(k) for k in
                                      ("code", "sg_status_list", "created_at", "created_by",
                                       "updated_at", "cached_display_name")}, default=str))
            rows.append(f"  relationships present: {sorted(back.json()['data'].get('relationships', {}))}")

            # link it to a Sequence, the field a client actually uses
            seq = search("sequences", [["project", "is", {"type": "Project", "id": SANDBOX}]],
                         ["code"], size=1)
            sq = seq.json()["data"][0] if seq.ok and seq.json()["data"] else None
            if sq is None:
                rs = c.post("/entity/sequences", headers=JSON,
                            json={"project": {"type": "Project", "id": SANDBOX}, "code": f"{TAG}_seq"})
                sq = rs.json()["data"] if rs.ok else None
                if sq:
                    made.add("sequences", sq["id"])
                else:
                    rows.append(f"  sequence create {rs.status_code} {whole_error(rs)}")
            if sq:
                pr = c.put(f"/entity/shots/{sid}", headers=JSON,
                           json={"sg_sequence": {"type": "Sequence", "id": sq["id"]}})
                rows.append(f"  PUT sg_sequence {{Sequence,id}} -> {pr.status_code} "
                            + (json.dumps((pr.json()["data"]["relationships"]["sg_sequence"] or {}).get("data"))
                               if pr.ok else whole_error(pr)))
                pr = c.put(f"/entity/shots/{sid}", headers=JSON,
                           json={"sg_sequence": {"type": "Shot", "id": sid}})
                rows.append(f"  PUT sg_sequence {{Shot,id}} (valid_types is ['Sequence']) -> "
                            f"{pr.status_code} "
                            + (json.dumps((pr.json()["data"]["relationships"]["sg_sequence"] or {}).get("data"))
                               if pr.ok else whole_error(pr)[:300]))
            pr = c.put(f"/entity/shots/{sid}", headers=JSON, json={"step_0": "ip"})
            rows.append(f"  PUT step_0 -> {pr.status_code} " + ("" if pr.ok else whole_error(pr)[:260]))
            pr = c.put(f"/entity/shots/{sid}", headers=JSON, json={"code": None})
            rows.append(f"  PUT code null (mandatory) -> {pr.status_code} "
                        + ("" if pr.ok else whole_error(pr)[:260]))

_lib.emit("entity_types/Shot", "\n".join(rows), env)
