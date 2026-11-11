"""Q: what do revive, update and retire answer on a name that was never used, on a retired field
and on a live one, and does a project-scoped `visible` write take its project anywhere but the body
or the query?

A client that revives before it creates has to tell "nothing to revive" from "revived", and one
that updates has to tell "gone" from "refused". No name is spent: the never-used name is only
addressed, never created, and the retired and live cases use `sg_zzprobe_115_visibility` on
Version, which probe 115 spent. It is retired again on exit. `visible` is written only with the
sandbox project's id.

Read-only half: `GET /schema/permission_groups` and its two children, which `/spec.json` names, as
the script. What a person below Admin gets from a schema write is not measured here: it needs that
person's session.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
out = []
TYPE = "Version"
SPENT, NEVER = "sg_zzprobe_115_visibility", "sg_zzprobe_119_never_used"
BASE = f"/schema/{TYPE}/fields"


def errs(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text[:400]
    if isinstance(j, dict) and "errors" in j:
        return json.dumps([{k: e.get(k) for k in ("status", "code", "title", "source", "detail")
                            if e.get(k) is not None} for e in j["errors"]])
    return json.dumps(j)[:200]


def head(t):
    out.append(f"\n\n===== {t}")


def prop(**kv):
    return [{"property_name": k, "value": v} for k, v in kv.items()]


def call(label, method, name, **kw):
    assert name.startswith("sg_zzprobe_"), name
    r = c.request(method, f"{BASE}/{name}", **kw)
    sent = {k: kw[k] for k in ("params", "json") if k in kw}
    out.append(f"{method} .../{name}  {json.dumps(sent) if sent else ''}\n"
               f"  [{label}] -> {r.status_code}  {errs(r)}")
    return r


def live(name):
    return c.get(f"{BASE}/{name}").status_code == 200


head("GET /schema/permission_groups, as the script")
g = c.get("/schema/permission_groups")
groups = g.json().get("data") or []
out.append(f"-> {g.status_code}, {len(groups)} group(s): {json.dumps(groups)}")
for q in ("HumanUser", "ApiUser"):
    r = c.get("/schema/permission_groups", params={"permission_rule_set_entity_type": q})
    out.append(f"  ?permission_rule_set_entity_type={q} -> {r.status_code}, "
               f"{len(r.json().get('data') or [])} group(s)")
if groups:
    code = groups[0]["code"]
    r = c.get(f"/schema/permission_groups/{code}/entity_types/{TYPE}")
    out.append(f"GET .../{code}/entity_types/{TYPE} -> {r.status_code}  {r.text[:700]}")
    r = c.get(f"/schema/permission_groups/{code}/entity_types/{TYPE}/fields")
    f = (r.json().get("data") or {}).get("fields") or []
    out.append(f"GET .../{code}/entity_types/{TYPE}/fields -> {r.status_code}, {len(f)} fields, "
               f"{len(r.content)} bytes; first: {json.dumps(f[0]) if f else None}")
    r = c.get(f"/schema/permission_groups/zz_no_such_group/entity_types/{TYPE}")
    out.append(f"GET .../zz_no_such_group/entity_types/{TYPE} -> {r.status_code}  {errs(r)}")

if not _lib.writes_allowed():
    out.append("\n\n===== writes skipped: run with --write")
    _lib.emit("119_field_absent_retired_live", "\n".join(out), env)
    raise SystemExit

SB = _lib.sandbox_id(c, env)
others = [p for p in _lib.sample_projects(c, env) if p != SB]


def vis():
    row = []
    for lab, pid in [("site", None), ("sandbox", SB)] + [(f"sample {i + 1}", p) for i, p in enumerate(others)]:
        r = c.get(f"{BASE}/{SPENT}", params={"project_id": pid} if pid else {})
        row.append(f"{lab}: {r.json()['data']['visible']['value'] if r.ok else r.status_code}")
    return "  ".join(row)


head(f"a name never used, {NEVER}")
call("GET", "GET", NEVER)
call("revive, in the body", "POST", NEVER, json={"revive": True})
call("revive, in the query", "POST", NEVER, params={"revive": "true"})
call("update", "PUT", NEVER, json={"properties": prop(description="x")})
call("update of visible with a project", "PUT", NEVER,
     json={"properties": prop(visible=False), "project_id": SB})
call("retire", "DELETE", NEVER)
out.append(f"  live after all six: {live(NEVER)}")
r = c.post(BASE, json={})
out.append(f"POST {BASE}  {{}} -> {r.status_code}  {errs(r)}")

head(f"a retired field, {SPENT}")
if live(SPENT):
    raise SystemExit(f"{SPENT} is live; probe 115 leaves it retired")
call("GET", "GET", SPENT)
call("update", "PUT", SPENT, json={"properties": prop(description="zzprobe 119 on retired")})
call("update of visible with a project", "PUT", SPENT,
     json={"properties": prop(visible=False), "project_id": SB})
call("retire again", "DELETE", SPENT)
r = c.post(BASE, json={"data_type": "text", "properties": prop(name="zzprobe 115 visibility")})
out.append(f"POST {BASE}  the display name that derives it -> {r.status_code}  {r.text}")
out.append(f"  live after: {live(SPENT)}")

try:
    head("the same field, live")
    call("revive", "POST", SPENT, json={"revive": True})
    d = c.get(f"{BASE}/{SPENT}").json()["data"]
    before = json.dumps(d, sort_keys=True)
    out.append(f"  live: {live(SPENT)}; description {json.dumps(d['description']['value'])}")
    call("revive, while live", "POST", SPENT, json={"revive": True})
    call("revive in the query, while live", "POST", SPENT, params={"revive": "true"})
    after = json.dumps(c.get(f"{BASE}/{SPENT}").json()["data"], sort_keys=True)
    n = sum(1 for k in c.get(BASE).json()["data"] if k.startswith(SPENT))
    out.append(f"  record identical after both: {before == after}; fields named {SPENT}*: {n}")

    head("where a visible write takes its project")
    out.append(f"  visible  {vis()}")
    call("project_id inside the property", "PUT", SPENT,
         json={"properties": [{"property_name": "visible", "value": False, "project_id": SB}]})
    out.append(f"  visible  {vis()}")
    call("project as an entity in the body", "PUT", SPENT,
         json={"properties": prop(visible=False), "project": {"type": "Project", "id": SB}})
    out.append(f"  visible  {vis()}")
    call("project_id in the body", "PUT", SPENT, json={"properties": prop(visible=False), "project_id": SB})
    out.append(f"  visible  {vis()}")
    call("project_id in the query", "PUT", SPENT, json={"properties": prop(visible=True)},
         params={"project_id": SB})
    out.append(f"  visible  {vis()}")
finally:
    r = c.delete(f"{BASE}/{SPENT}")
    out.append(f"\nretired {SPENT} -> {r.status_code}; live after: {live(SPENT)}")

_lib.emit("119_field_absent_retired_live", "\n".join(out), env)
