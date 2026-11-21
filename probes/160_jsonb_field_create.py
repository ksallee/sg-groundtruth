"""Q: can a custom `jsonb` field be created over REST, on Project or any type, and if so does it store
and filter as `Note.meta` does?

sg-onset stores two settings lists as JSON (sg-onset #110). A text field holds a string the client
parses; a `jsonb` field would hold the value and filter on it (`field_types/jsonb`). The site has two
`jsonb` fields, both stock. `/spec.json` enumerates the `data_type` a create takes; this prints that
list, then sends `POST /schema/<Type>/fields` with `data_type: jsonb` on Project, Version and the
first enabled custom slot, and `serializable` on Project, the other JSON type. A create that lands is
written on the sandbox Project (or a sandbox row), read back, updated, filtered and retired.

Writes behind `--write`: fields `sg_zzprobe_160_*` if any create lands, retired before exit.

    python probes/160_jsonb_field_create.py [--write]
"""
import json

import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
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


spec = c.get("/spec.json").json()
enum = spec["components"]["schemas"]["CreateFieldRequest"]["properties"]["data_type"].get("enum")
out(f"/spec.json CreateFieldRequest.data_type enum: {enum}")
out(f"  jsonb listed: {'jsonb' in (enum or [])}; serializable listed: {'serializable' in (enum or [])}")
_lib.emit("160_jsonb_field_create", "\n".join(rows), env)
if not _lib.writes_allowed():
    raise SystemExit("\nread-only half done; --write sends the creates")

rows.clear()
schema = c.get("/schema").json()["data"]
CE = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())[0]
made = []
try:
    out("===== POST /schema/<Type>/fields")
    for typ, label, dt in (("Project", "Project", "jsonb"), ("Version", "Version", "jsonb"),
                           (CE, "<custom slot>", "jsonb"), ("Project", "Project", "serializable")):
        r = c.post(f"/schema/{typ}/fields", json={"data_type": dt, "properties": [
            {"property_name": "name", "value": f"zzprobe 160 {dt}"}]})
        if r.status_code == 201:
            name = r.json()["links"]["self"].rsplit("/", 1)[-1]
            made.append((typ, name, dt))
            out(f"  {label} {dt} -> 201 {name}")
        else:
            out(f"  {label} {dt} -> {r.status_code} {errs(r)}")

    for typ, name, dt in made:
        if typ != "Project":
            continue
        out(f"\n===== Project.{name} ({dt}) on the sandbox Project")
        d = c.get(f"/schema/Project/fields/{name}").json()["data"]
        out(f"  schema data_type {d['data_type']['value']} editable {d['editable']['value']} "
            f"properties {json.dumps(d['properties'])}")
        for v in ({"a": {"b": [1, 2, 3]}, "t": True, "n": None}, [{"x": 1}], "a string", None):
            w = c.put(f"/entity/projects/{SB}", json={name: v})
            back = c.get(f"/entity/projects/{SB}", params={"fields": name}).json()["data"]["attributes"].get(name)
            out(f"  PUT {json.dumps(v)} -> {w.status_code} {'' if w.ok else errs(w)}; reads {json.dumps(back)}")
        c.put(f"/entity/projects/{SB}", json={name: {"a": {"b": [1, 2, 3]}, "k": "v"}})
        for op, val in (("is", {"a": {"b": [1, 2, 3]}, "k": "v"}), ("contains", {"a": {"b": [1]}}),
                        ("contains", {"k": "zz"}), ("definitely_not_an_operator", None)):
            s = c.post("/entity/projects/_search", headers=ARR, json={
                "filters": [["id", "is", SB], [name, op, val]], "fields": ["id"]})
            out(f"  filter {op} {json.dumps(val)} -> {s.status_code} "
                + (f"{len(s.json()['data'])} rows" if s.ok else errs(s)))
finally:
    for typ, name, dt in made:
        if typ == "Project":
            c.put(f"/entity/projects/{SB}", json={name: None})
        r = c.delete(f"/schema/{typ}/fields/{name}")
        out(f"  retired {typ}.{name} -> {r.status_code}")
    _lib.emit("160_jsonb_field_create (write)", "\n".join(rows), env)
