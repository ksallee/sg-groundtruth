"""Q: is a field's `visible` a per-project value, and can it be read and written for one project
without touching the others?

Read-only by default: `GET /schema/<Type>/fields` on Version, Shot and Task at site scope, with the
sandbox project and with every sample project, comparing `visible` field by field, then the same for
one field through `GET /schema/<Type>/fields/<field>`.

`--write` creates one text field on Version, `sg_zzprobe_115_visibility`, and writes `visible` only on
it and only with the sandbox project's id. Every sample project and the site-scope reading are read
before and after each write, because a server that ignored the project would otherwise change
projects this probe may only read. The field is retired on the way out. The name stays spent.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
WRITE = _lib.writes_allowed()
out = []
TYPE, DISPLAY, PREFIX = "Version", "zzprobe 115 visibility", "sg_zzprobe_115_"


def body_of(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text[:300]
    if isinstance(j, dict) and "errors" in j:
        return json.dumps(j["errors"])
    return json.dumps(j)[:260]


def call(label, method, path, **kw):
    r = c.request(method, path, **kw)
    sent = {k: kw[k] for k in ("params", "json") if k in kw}
    out.append(f"{method} {path}  {json.dumps(sent) if sent else ''}\n"
               f"  [{label}] -> {r.status_code}  {body_of(r)}")
    return r


def head(t):
    out.append(f"\n\n===== {t}")


SB = _lib.sandbox_id(c, env)
others = [p for p in _lib.sample_projects(c, env) if p != SB]
scopes = [("site", None), ("sandbox", SB)] + [(f"sample {i + 1}", p) for i, p in enumerate(others)]


def listing(t, pid):
    r = c.get(f"/schema/{t}/fields", params={"project_id": pid} if pid else {})
    return r.json()["data"], len(r.content)


# --- 1. the listing, per scope ------------------------------------------------------------------
head("GET /schema/<Type>/fields, `visible` per scope")
hidden_somewhere = None
for t in ("Version", "Shot", "Task"):
    base, n0 = listing(t, None)
    no_key = [k for k, v in base.items() if "visible" not in v]
    out.append(f"{t}: {len(base)} fields, {n0} bytes at site scope; visible false: "
               f"{sum(1 for v in base.values() if v['visible']['value'] is False)}; "
               f"fields with no `visible` key: {len(no_key)}")
    per = {}
    for label, pid in scopes[1:]:
        d, n = listing(t, pid)
        per[label] = {k for k, v in d.items() if v["visible"]["value"] is False}
        other_keys = sorted({p for k in d for p in d[k] if d[k][p] != base[k].get(p)} - {"visible"})
        out.append(f"  {label}: {n} bytes, same field names: {set(d) == set(base)}, visible false: "
                   f"{len(per[label])}, of them visible.editable true: "
                   f"{sum(1 for k in per[label] if d[k]['visible']['editable'])}, "
                   f"other keys that differ from site scope: {other_keys}")
    sets = list(per.values())
    if len(sets) > 1:
        out.append(f"  hidden in the sandbox only: {len(sets[0] - sets[1])}, in sample 1 only: "
                   f"{len(sets[1] - sets[0])}, in both: {len(sets[0] & sets[1])}")
        if hidden_somewhere is None and sets[1] - sets[0]:
            hidden_somewhere = (t, sorted(sets[1] - sets[0])[0])

if hidden_somewhere:
    t, f = hidden_somewhere
    head(f"GET /schema/{t}/fields/<field>, one field hidden in sample 1 and not in the sandbox")
    _lib.note_names(f)
    for label, pid in scopes:
        r = c.get(f"/schema/{t}/fields/{f}", params={"project_id": pid} if pid else {})
        out.append(f"  {label}: {r.status_code} visible {json.dumps(r.json()['data']['visible'])}")
    r = c.get(f"/schema/{t}/fields/{f}", params={"project_id": 999999999})
    out.append(f"  project_id 999999999: {r.status_code} visible "
               f"{json.dumps((r.json().get('data') or {}).get('visible')) if r.ok else body_of(r)}")
    r = c.get(f"/schema/{t}/fields", params={"project_id": 999999999})
    d = r.json().get("data") or {}
    out.append(f"  the listing with project_id 999999999: {r.status_code}, {len(d)} fields, visible "
               f"false: {sum(1 for v in d.values() if v['visible']['value'] is False)}")

head("GET /schema and /schema/<Type>, the type's own `visible` per scope")
for label, pid in scopes:
    d = c.get("/schema", params={"project_id": pid} if pid else {}).json()["data"]
    out.append(f"  {label}: {len(d)} types, visible false: "
               f"{sum(1 for v in d.values() if v['visible']['value'] is False)}")

if not WRITE:
    out.append("\n\n===== writes skipped: run with --write")
    _lib.emit("115_field_visibility_per_project", "\n".join(out), env)
    raise SystemExit

# --- 2. one throwaway field ---------------------------------------------------------------------
head(f"create {DISPLAY!r} on {TYPE}")
r = call("create", "POST", f"/schema/{TYPE}/fields",
         json={"data_type": "text", "properties": [{"property_name": "name", "value": DISPLAY}]})
if r.status_code == 201:
    NAME = r.json()["links"]["self"].rsplit("/", 1)[-1]
elif "retired field" in r.text:     # a second run: the name is spent, so take it back
    NAME = PREFIX + "visibility"
    call("revive, the name was spent by an earlier run", "POST", f"/schema/{TYPE}/fields/{NAME}",
         json={"revive": True})
else:
    _lib.emit("115_field_visibility_per_project", "\n".join(out), env)
    raise SystemExit("create failed")
assert NAME.startswith(PREFIX), NAME
FIELD = f"/schema/{TYPE}/fields/{NAME}"
out.append(f"programmatic name: {NAME}")


def vis(pid):
    r = c.get(FIELD, params={"project_id": pid} if pid else {})
    return r.json()["data"]["visible"] if r.status_code == 200 else f"{r.status_code}"


def readings(note=""):
    row = "  ".join(f"{label}: {json.dumps(vis(pid))}" for label, pid in scopes)
    out.append(f"  reads{note}  {row}")


def prop(**kv):
    return [{"property_name": k, "value": v} for k, v in kv.items()]


try:
    head("the default on a new field")
    readings()
    for label, pid in scopes:
        d, _ = listing(TYPE, pid)
        out.append(f"  listing at {label}: present {NAME in d}, "
                   f"visible {json.dumps(d.get(NAME, {}).get('visible'))}")

    head("write `visible`")
    call("false, no project_id", "PUT", FIELD, json={"properties": prop(visible=False)})
    readings()
    call("false, project_id in the body", "PUT", FIELD,
         json={"properties": prop(visible=False), "project_id": SB})
    readings()
    d, _ = listing(TYPE, SB)
    out.append(f"  listing at sandbox: present {NAME in d}, visible {json.dumps(d[NAME]['visible'])}")
    call("false again, the value it already holds", "PUT", FIELD,
         json={"properties": prop(visible=False), "project_id": SB})
    call("true, project_id in the query only", "PUT", FIELD,
         json={"properties": prop(visible=True)}, params={"project_id": SB})
    readings()
    call("true, project_id in the body", "PUT", FIELD,
         json={"properties": prop(visible=True), "project_id": SB})
    readings()
    call("false, project_id that does not exist", "PUT", FIELD,
         json={"properties": prop(visible=False), "project_id": 999999999})
    call("the string \"false\", project_id in the body", "PUT", FIELD,
         json={"properties": prop(visible="false"), "project_id": SB})
    readings()
    call("true, to reset", "PUT", FIELD, json={"properties": prop(visible=True), "project_id": SB})

    head("`visible` and `description` in one PUT with project_id")
    call("both", "PUT", FIELD,
         json={"properties": prop(visible=False, description="zzprobe 115 d1"), "project_id": SB})
    readings()
    for label, pid in scopes:
        r = c.get(FIELD, params={"project_id": pid} if pid else {})
        out.append(f"  description at {label}: {json.dumps(r.json()['data']['description']['value'])}")
    call("`description` alone with project_id", "PUT", FIELD,
         json={"properties": prop(description="zzprobe 115 d2"), "project_id": SB})
    r = c.get(FIELD)
    out.append(f"  description at site: {json.dumps(r.json()['data']['description']['value'])}")

    head("records, while the field is hidden in the sandbox")
    r = c.get("/entity/versions", params={"filter[project.Project.id]": SB, "fields": NAME,
                                          "page[size]": 1})
    out.append(f"GET /entity/versions?fields={NAME} in the sandbox -> {r.status_code}, "
               f"rows {len(r.json().get('data') or [])}, field in attributes: "
               f"{any(NAME in (x.get('attributes') or {}) for x in r.json().get('data') or [])}")

    head("retire and revive, while hidden in the sandbox")
    call("retire", "DELETE", FIELD)
    call("revive", "POST", FIELD, json={"revive": True})
    readings(" after the revive")
finally:
    r = c.delete(FIELD)
    out.append(f"\nretired {NAME} -> {r.status_code}; live after: {c.get(FIELD).status_code == 200}")

_lib.emit("115_field_visibility_per_project", "\n".join(out), env)
