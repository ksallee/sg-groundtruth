"""Q: do create, per-project `visible`, retire, the retired-name refusal and revive behave on a
custom entity type and on a type with no `project` field as they do on Version?

Every schema write before this was measured on Version. Writes only, behind `--write`: one text
field, `sg_zzprobe_118_other_type`, on the first enabled `CustomEntityNN` and on Tag, which is stock
and has no `project` field. The probed site has no `CustomNonProjectEntityNN` enabled; if one were,
it would be used as a third type. `visible` is written only with the sandbox project's id, and the
site scope and every sample project are read after each write. Both fields are retired on exit.
"""
import json
import re

import _lib

env = _lib.load_env()
c = _lib.client()
out = []
DISPLAY, PREFIX = "zzprobe 118 other type", "sg_zzprobe_118_"

if not _lib.writes_allowed():
    raise SystemExit("probe 118 only writes; run with --write")

SB = _lib.sandbox_id(c, env)
others = [p for p in _lib.sample_projects(c, env) if p != SB]
scopes = [("site", None), ("sandbox", SB)] + [(f"sample {i + 1}", p) for i, p in enumerate(others)]


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
    return ""


def prop(**kv):
    return [{"property_name": k, "value": v} for k, v in kv.items()]


types_ = c.get("/schema").json()["data"]
custom = sorted(t for t in types_ if re.fullmatch(r"CustomEntity\d\d", t))
non_project = sorted(t for t in types_ if re.fullmatch(r"CustomNonProjectEntity\d\d", t))
out.append(f"enabled CustomEntityNN: {len(custom)}, CustomNonProjectEntityNN: {len(non_project)}")
targets = [(t, label) for t, label in ((custom[0] if custom else None, "a custom entity"),
                                       (non_project[0] if non_project else None, "a custom non-project entity"),
                                       ("Tag", "a stock type with no project field")) if t]

for TYPE, label in targets:
    fields = c.get(f"/schema/{TYPE}/fields").json()["data"]
    out.append(f"\n\n===== {TYPE} ({label}): {len(fields)} fields, has a `project` field: "
               f"{'project' in fields}")
    body = {"data_type": "text", "properties": prop(name=DISPLAY, description="zzprobe 118 desc")}
    r = c.post(f"/schema/{TYPE}/fields", json=body)
    out.append(f"POST /schema/{TYPE}/fields  {json.dumps(body)} -> {r.status_code}  {errs(r)}")
    if r.status_code != 201:
        continue
    NAME = r.json()["links"]["self"].rsplit("/", 1)[-1]
    assert NAME.startswith(PREFIX), NAME
    FIELD = f"/schema/{TYPE}/fields/{NAME}"
    out.append(f"  links.self {r.json()['links']['self']}")

    def vis():
        row = []
        for lab, pid in scopes:
            g = c.get(FIELD, params={"project_id": pid} if pid else {})
            row.append(f"{lab}: {json.dumps(g.json()['data']['visible']) if g.ok else g.status_code}")
        return "  ".join(row)

    try:
        d = c.get(FIELD).json()["data"]
        out.append(f"  reads data_type {d['data_type']['value']}, description "
                   f"{json.dumps(d['description']['value'])}, entity_type {d['entity_type']['value']}")
        out.append(f"  visible  {vis()}")
        r = c.put(FIELD, json={"properties": prop(visible=False), "project_id": SB})
        out.append(f"PUT visible false, project_id sandbox -> {r.status_code}  {errs(r)}\n  visible  {vis()}")
        r = c.put(FIELD, json={"properties": prop(visible=True), "project_id": SB})
        out.append(f"PUT visible true, project_id sandbox -> {r.status_code}  {errs(r)}\n  visible  {vis()}")
        r = c.put(FIELD, json={"properties": prop(description="zzprobe 118 desc 2")})
        out.append(f"PUT description -> {r.status_code}  {errs(r)}; reads "
                   f"{json.dumps(c.get(FIELD).json()['data']['description']['value'])}")
        r = c.delete(FIELD)
        out.append(f"DELETE -> {r.status_code}; GET -> {c.get(FIELD).status_code}; listed: "
                   f"{NAME in c.get(f'/schema/{TYPE}/fields').json()['data']}")
        r = c.post(f"/schema/{TYPE}/fields", json=body)
        out.append(f"POST the same display name -> {r.status_code}  {errs(r)}")
        r = c.post(FIELD, json={})
        out.append(f"POST {{}} to the field path -> {r.status_code}  {errs(r)}")
        r = c.post(FIELD, json={"revive": True})
        d = (c.get(FIELD).json().get("data") or {})
        out.append(f"POST {{\"revive\": true}} -> {r.status_code}  {errs(r)}; GET -> "
                   f"{c.get(FIELD).status_code}, data_type {d.get('data_type', {}).get('value')}, "
                   f"description {json.dumps(d.get('description', {}).get('value'))}")
    finally:
        r = c.delete(FIELD)
        out.append(f"DELETE -> {r.status_code}; live after: {c.get(FIELD).status_code == 200}")

_lib.emit("118_field_writes_other_types", "\n".join(out), env)
