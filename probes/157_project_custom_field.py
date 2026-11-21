"""Q: can a custom text field be created on Project over REST, with what body, by whom, and how does it
read back in the schema?

sg-onset keeps two settings lists as JSON in text fields on Project (sg-onset #110). Probe 132
measured field creation by permission group on a custom slot; Project is the type sg-onset writes,
and it is site-wide, not project-scoped. Each caller sends the same create, a text field with a
description, named `zzprobe 157 <group>`: the script acting through `sudo_as_login` (probe 027) as
one active impersonatable person per permission group. The field that lands is read back from
`GET /schema/Project/fields/<field>`, with and without `project_id`, from the listing, and from the
sandbox Project row.

Read-only half: who can be measured, and whether the names sg-onset wants are live. `--write` sends
the creates; every field that lands is retired before exit and stays in the Trash. A rerun for a
group added later names it, so a landed name is not spent twice (probe 019):

    python probes/157_project_custom_field.py [--write] [--only Manager]
"""
import json
import sys

import _lib
from sg_groundtruth.client import FPT

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
SB = _lib.sandbox_id(c, env)
rows = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text
    return json.dumps(j.get("errors", j))


def pick(d):
    """The parts of a schema field a caller reads, without the per-project noise."""
    keep = ("name", "description", "data_type", "entity_type", "editable", "visible", "mandatory",
            "unique", "properties", "ui_value_displayable")
    return {k: d.get(k) for k in keep if k in d}


users = c.post("/entity/human_users/_search", headers=ARR, json={
    "filters": [["sg_status_list", "is", "act"], ["can_impersonate_this_user", "is", True]],
    "fields": ["login", "permission_rule_set", "projects"], "page": {"size": 500}}).json()["data"]
by_group = {}
for u in users:
    g = (u["relationships"]["permission_rule_set"]["data"] or {}).get("name")
    by_group.setdefault(g, u["attributes"]["login"])
    _lib.note_names(u["attributes"]["login"])
sets = c.get("/entity/permission_rule_sets", params={"fields": "display_name,entity_type",
                                                     "page[size]": 100}).json()["data"]
human = sorted(s["attributes"]["display_name"] for s in sets if s["attributes"]["entity_type"] == "HumanUser")
out(f"HumanUser permission groups: {human}")
out(f"groups with an active, impersonatable person: {sorted(by_group)}")
out(f"groups not measurable: {sorted(set(human) - set(by_group))}")

out("\n===== the names sg-onset wants, live on Project?")
for name in ("sg_onset_templates", "sg_onset_reference_kinds"):
    r = c.get(f"/schema/Project/fields/{name}")
    out(f"  GET /schema/Project/fields/{name} -> {r.status_code} {'' if r.ok else errs(r)}")
listing = c.get("/schema/Project/fields").json()["data"]
out(f"  GET /schema/Project/fields: {len(listing)} fields, "
    f"{sum(1 for f in listing.values() if f['data_type']['value'] == 'text')} text")

_lib.emit("157_project_custom_field", "\n".join(rows), env)
if not _lib.writes_allowed():
    raise SystemExit("\nread-only half done; --write sends the creates")

rows.clear()
made = []
only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
try:
    out("===== POST /schema/Project/fields, a text field with a description, as each person")
    for group, login in sorted(by_group.items(), key=lambda x: x[0] != "Artist"):
        if only and group not in only:
            continue
        p = FPT.from_env(env, sudo_as_login=login)
        tag = "".join(ch for ch in group.lower() if ch.isalnum())
        body = {"data_type": "text", "properties": [
            {"property_name": "name", "value": f"zzprobe 157 {tag}"},
            {"property_name": "description", "value": "zzprobe 157: a JSON list, written by an app"}]}
        r = p.post("/schema/Project/fields", json=body)
        if r.status_code == 201:
            name = r.json()["links"]["self"].rsplit("/", 1)[-1]
            made.append(name)
            out(f"  {group}: -> 201 links.self .../{name}")
            out(f"    body keys {sorted(r.json())}, data keys {sorted(r.json()['data'])}")
        else:
            out(f"  {group}: -> {r.status_code} {errs(r)}")

    if made:
        f = made[0]
        out(f"\n===== {f}, read back")
        d = c.get(f"/schema/Project/fields/{f}").json()["data"]
        out(f"  GET /schema/Project/fields/{f}\n    {json.dumps(pick(d))}")
        d2 = c.get(f"/schema/Project/fields/{f}", params={"project_id": SB}).json()["data"]
        out(f"  ...?project_id=<sandbox>  visible {d2.get('visible')}  editable {d2.get('editable')}")
        out(f"    differs from the site read in: {sorted(k for k in d2 if d2.get(k) != d.get(k))}")
        lst = c.get("/schema/Project/fields").json()["data"]
        out(f"  in GET /schema/Project/fields: {f in lst}; entry equal to the single read: {lst.get(f) == d}")
        r = c.get(f"/entity/projects/{SB}", params={"fields": f})
        out(f"  GET /entity/projects/<sandbox>?fields={f} -> {r.status_code} "
            f"attributes {json.dumps(r.json()['data']['attributes'])}")
        r = c.get(f"/entity/projects/{SB}")
        out(f"  GET /entity/projects/<sandbox>, no fields -> {r.status_code}, "
            f"{f} in attributes: {f in r.json()['data']['attributes']}")
        art = by_group.get("Artist")
        if art:
            a = FPT.from_env(env, sudo_as_login=art)
            r = a.get(f"/schema/Project/fields/{f}", params={"project_id": SB})
            out(f"  as the Artist, ...?project_id=<sandbox> -> {r.status_code} "
                + (f"visible {r.json()['data'].get('visible')} editable {r.json()['data'].get('editable')}"
                   if r.ok else errs(r)))
finally:
    for name in made:
        r = c.delete(f"/schema/Project/fields/{name}")
        out(f"  retired Project.{name} -> {r.status_code}")
    left = [k for k in c.get("/schema/Project/fields").json()["data"] if "zzprobe_157" in k]
    out(f"  zzprobe_157 fields live on Project at exit: {left}")
    _lib.emit("157_project_custom_field (write)", "\n".join(rows), env)
