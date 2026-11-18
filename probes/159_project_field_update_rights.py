"""Q: who may update a custom field on a Project, and who may read it?

sg-onset writes its settings lists to text fields on Project (sg-onset #110) as the person signed
in. Probes 094 and 143 measured an Artist's row rights on Task, Shot and custom slots; Project is a
site-wide type with its own rules. The script makes a text field on Project, then each caller reads
it and writes it on the sandbox Project: the script, and the script acting through `sudo_as_login`
(probe 027) as one active impersonatable person per permission group, an Artist outside the sandbox
project as well as one in it. Before the writes, each caller's `editable` from
`GET /schema/Project/fields/<field>?project_id=` (probe 094), and every group's rights on Project as
the Admin person reads them from `GET /schema/permission_groups/<code>/entity_types/Project`.

Writes behind `--write`: the field `sg_zzprobe_159_rights` on Project, set on the sandbox Project,
set back to null and retired before exit. A rerun revives it rather than spending a second name.

    python probes/159_project_field_update_rights.py --write
"""
import json

import _lib
from sg_groundtruth.client import FPT

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 159 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
rows = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text[:2000]
    return json.dumps(j.get("errors", j))


users = c.post("/entity/human_users/_search", headers=ARR, json={
    "filters": [["sg_status_list", "is", "act"], ["can_impersonate_this_user", "is", True]],
    "fields": ["login", "permission_rule_set", "projects"], "page": {"size": 500}}).json()["data"]
people = {}
for u in users:
    g = (u["relationships"]["permission_rule_set"]["data"] or {}).get("name")
    inside = any(p["id"] == SB for p in u["relationships"]["projects"]["data"] or [])
    people.setdefault((g, inside), u["attributes"]["login"])
    _lib.note_names(u["attributes"]["login"])
out(f"active impersonatable people, by (group, in the sandbox project): {sorted(people)}")
callers = [("script (API Admin)", c)] + [
    (f"{g}, {'in' if inside else 'not in'} the sandbox", FPT.from_env(env, sudo_as_login=login))
    for (g, inside), login in sorted(people.items())]

admin = next((cl for label, cl in callers if label.startswith("Admin")), None)
if admin:
    out("\n===== every group's rights on Project, as the Admin person reads them")
    for g in admin.get("/schema/permission_groups").json()["data"]:
        r = admin.get(f"/schema/permission_groups/{g['code']}/entity_types/Project")
        if not r.ok:
            out(f"  {g['code']}: {r.status_code} {errs(r)}")
            continue
        a = r.json()["data"]["actions"]
        out(f"  {g['code']:<24} " + " ".join(f"{k} {(a.get(k) or {}).get('access', '-')}"
                                           for k in ("read", "create", "update", "retire", "delete"))
            + f"  update exceptions {json.dumps((a.get('update') or {}).get('field_exceptions'))}")
        cond = {k: v.get("conditions") for k, v in a.items() if isinstance(v, dict) and v.get("conditions")}
        if cond:
            out(f"    conditions {json.dumps(cond)}")

field = None
try:
    r = c.post("/schema/Project/fields", json={"data_type": "text", "properties": [
        {"property_name": "name", "value": "zzprobe 159 rights"}]})
    if r.status_code == 201:
        field = r.json()["links"]["self"].rsplit("/", 1)[-1]
        out(f"\nPOST /schema/Project/fields text 'zzprobe 159 rights' -> 201 {field}")
    else:
        rv = c.post("/schema/Project/fields/sg_zzprobe_159_rights", json={"revive": True})
        out(f"\nPOST /schema/Project/fields -> {r.status_code} {errs(r)}\n  revive -> {rv.status_code}")
        if not rv.ok:
            raise SystemExit(errs(rv))
        field = "sg_zzprobe_159_rights"
    c.put(f"/entity/projects/{SB}", json={field: "zzprobe 159 set by the script"})

    out("\n===== each caller: schema editable, read, write, on the sandbox Project")
    for label, cl in callers:
        tag = label.split(" (")[0].replace(" the sandbox", "").replace(",", "").lower()
        s = cl.get(f"/schema/Project/fields/{field}", params={"project_id": SB})
        ed = s.json()["data"]["editable"]["value"] if s.ok else f"{s.status_code} {errs(s)}"
        g = cl.get(f"/entity/projects/{SB}", params={"fields": field})
        seen = g.json()["data"]["attributes"].get(field, "(key absent)") if g.ok else f"{g.status_code} {errs(g)}"
        w = cl.put(f"/entity/projects/{SB}", json={field: f"zzprobe 159 by {tag}"})
        after = c.get(f"/entity/projects/{SB}", params={"fields": field}).json()["data"]["attributes"][field]
        out(f"  {label}\n    schema editable {ed}; GET reads {seen!r}")
        out(f"    PUT -> {w.status_code} {'' if w.ok else errs(w)}\n    value after, read by the script: {after!r}")
        n = cl.post("/entity/projects/_search", headers=ARR, json={
            "filters": [[field, "is", after]], "fields": [field]})
        out(f"    _search [{field} is <value>] -> {n.status_code} "
            + (f"{len(n.json()['data'])} rows" if n.ok else errs(n)))
finally:
    if field:
        r = c.put(f"/entity/projects/{SB}", json={field: None})
        out(f"\n  PUT {field} null on the sandbox Project -> {r.status_code}")
        r = c.delete(f"/schema/Project/fields/{field}")
        out(f"  retired Project.{field} -> {r.status_code}")
    left = [k for k in c.get("/schema/Project/fields").json()["data"] if "zzprobe_159" in k]
    out(f"  zzprobe_159 fields live on Project at exit: {left}")
    _lib.emit("159_project_field_update_rights", "\n".join(rows), env)
