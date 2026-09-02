"""Q: what does a write return, and what must be re-read?

Six production codebases each rediscovered part of this alone, none citing another. The claims: a create
honours extra `?fields` and an update does not; a batch create comes back thinner than a batch update;
an upload never names the final path. One row per operation.
"""
import base64
import json
import time

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []

# The same set on every verb, so any difference is the verb and not the syntax: plain, server-set,
# dotted through an entity field, and a bogus name as the quiet-drop control (probe 004).
REQ = ["code", "description", "sg_status_list", "created_at", "created_by",
       "project.Project.name", "entity.Shot.code", "sg_not_a_field"]
FIELDS = ",".join(REQ)

# 16x16 red PNG, so the probe needs no image library (probe 013)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAJ0lEQVR42mP8z8BQz0AEYBxVSF+F"
    "jIyM/xnpoxCfwlGFoy4cVUgPhQCq0Ags7T6l4wAAAABJRU5ErkJggg==")


def describe(status, d):
    """Size of the body, and which of REQ the literal key came back under. A dotted key counts only
    if the dotted string itself is present: `project` under relationships is not `project.Project.name`."""
    _lib.note_from(d)
    attrs, rels = d.get("attributes") or {}, d.get("relationships") or {}
    absent = [k for k in REQ if k not in attrs and k not in rels]
    return f"{status}  attributes={len(attrs)} relationships={len(rels)}  absent: {absent}"


def shape(r):
    if not r.ok:
        return f"{r.status_code} {json.dumps(r.json().get('errors', r.json()))}"
    return describe(r.status_code, r.json()["data"])


rows.append(f"asked for on every verb: {REQ}")

rows.append("\n=== control: the same field set on a read (probe 003 says dotted reads work)")
PROJECT = _lib.sample_projects(c, env)[0]
r = c.post("/entity/versions/_search", headers=ARR, json={
    "filters": [["project", "is", {"type": "Project", "id": PROJECT}], ["entity", "is_not", None]],
    "fields": REQ, "page": {"size": 1}})
if r.ok and r.json()["data"]:
    d = r.json()["data"][0]
    rows.append("  POST _search  " + describe(r.status_code, d))
    rows.append(f"    attributes: {sorted(d['attributes'])}")

rows.append("\n=== is there a batch endpoint over REST?")
rows.append("  GET is no discriminator: the known POST-only /_search route 404s on GET too, so a 404")
rows.append("  cannot tell `no such route` from `wrong verb`. Only POST settles it.")
for path in ("/entity/versions/_search", "/entity/_batch", "/batch", "/entity/versions/_batch"):
    r = c.get(path)
    rows.append(f"    GET  {path:<26} {r.status_code}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; the write half needs --write)")
    _lib.emit("024_read_after_write", "\n".join(rows), env)
    raise SystemExit(0)

SANDBOX = _lib.sandbox_id(c, env)

with _lib.Created(c) as made:
    shots = c.get("/entity/shots", params={"filter[project.Project.id]": SANDBOX,
                                           "fields": "code", "page[size]": 1}).json()
    _lib.note_from(shots)
    if shots["data"]:
        shot_id = shots["data"][0]["id"]
    else:
        shot_id = made.add("shots", c.post("/entity/shots", json={
            "project": {"type": "Project", "id": SANDBOX},
            "code": "zzprobe_024_sh010"}).json()["data"]["id"])

    def body(code, **extra):
        b = {"project": {"type": "Project", "id": SANDBOX}, "code": code,
             "description": "probe 024", "sg_status_list": "rev",
             "entity": {"type": "Shot", "id": shot_id}}
        b.update(extra)
        return b

    def create(label, params=None, **extra):
        r = c.post("/entity/versions", params=params, json=body(f"zzprobe_024_{label}", **extra))
        made.add("versions", r.json()["data"]["id"])
        rows.append(f"  {label:<14} " + shape(r))
        return r.json()["data"]

    rows.append("\n=== CREATE  POST /entity/versions")
    a = create("a")
    rows.append(f"                 attributes: {sorted(a['attributes'])}")
    b = create("b", flagged=True, frame_count=10, sg_path_to_movie="/mnt/projects/demo_show/x.mov")
    rows.append(f"                 attributes: {sorted(b['attributes'])}")
    rows.append("                 => the create body's own fields are echoed; untouched ones are not")
    d = create("c", params={"fields": FIELDS})
    vid = d["id"]
    rows.append(f"                 attributes: {sorted(d['attributes'])}")
    rows.append(f"  a link is returned whole, no second read needed for its name:\n"
                f"    relationships.entity = {json.dumps(d['relationships']['entity']['data'])}")

    rows.append("\n=== UPDATE  on that same Version")
    for verb in ("PUT", "PATCH"):
        for label, params in (("no ?fields ", None), ("?fields=...", {"fields": FIELDS})):
            r = c.request(verb, f"/entity/versions/{vid}", params=params,
                          json={"description": f"probe 024 {verb} {label.strip()}"})
            rows.append(f"  {verb:<5} {label}  " + shape(r))

    rows.append("\n=== BATCH  the endpoint enumerates its own contract, one 400 at a time")
    for label, batch in (
            ("array body", [{"request_type": "create", "entity": "Version"}]),
            ("no requests key", {"entity": "Version"}),
            ("request missing entity", {"requests": [{"request_type": "create"}]}),
            ("request missing data", {"requests": [{"request_type": "create", "entity": "Version"}]}),
            ("request_type read", {"requests": [{"request_type": "read", "entity": "Version",
                                                 "data": {}}]}),
            ("update via entity_id", {"requests": [{"request_type": "update", "entity": "Version",
                                                    "entity_id": vid, "data": {"description": "x"}}]})):
        r = c.post("/entity/_batch", json=batch)
        rows.append(f"  {label:<22} {r.status_code} {json.dumps(r.json().get('errors', ['ok'])[0])}")
    r = c.post("/entity/_batch", headers=ARR, json={"requests": []})
    rows.append(f"  vendor Content-Type    {r.status_code} {json.dumps(r.json()['errors'][0])}")

    rows.append("\n  one batch, a create and an update together:")
    r = c.post("/entity/_batch", params={"fields": FIELDS}, json={"requests": [
        {"request_type": "create", "entity": "Version",
         "data": {"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_024_bc",
                  "description": "batch create", "entity": {"type": "Shot", "id": shot_id}}},
        {"request_type": "update", "entity": "Version", "record_id": vid,
         "data": {"description": "batch update"}}]})
    for i, row in enumerate(r.json()["data"]):
        d = row.get("data", row)
        if d.get("id"):
            made.add("versions", d["id"])
        rows.append(f"    row {i} ({'create' if i == 0 else 'update'})  outer keys={sorted(row)}  "
                    + describe(r.status_code, d))

    rows.append("\n  a delete row, and whether a failing row rolls the batch back:")
    r = c.post("/entity/_batch", json={"requests": [
        {"request_type": "create", "entity": "Version",
         "data": {"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_024_bd"}}]})
    tmp = r.json()["data"][0]["data"]["id"]
    r = c.post("/entity/_batch", json={"requests": [
        {"request_type": "delete", "entity": "Version", "record_id": tmp}]})
    rows.append(f"    delete row -> {r.status_code} {json.dumps(r.json()['data'][0])}")
    r = c.post("/entity/_batch", json={"requests": [
        {"request_type": "create", "entity": "Version",
         "data": {"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_024_atomic"}},
        {"request_type": "update", "entity": "Version", "record_id": 999999999,
         "data": {"description": "no such row"}}]})
    rows.append(f"    good create + bad update -> {r.status_code} "
                f"{json.dumps(r.json()['errors'][0]['detail'])}")
    s = c.post("/entity/versions/_search", headers=ARR, json={
        "filters": [["project", "is", {"type": "Project", "id": SANDBOX}],
                    ["code", "is", "zzprobe_024_atomic"]], "fields": ["code"]})
    for d in s.json()["data"]:
        made.add("versions", d["id"])
    rows.append(f"    rows the good create left behind: {len(s.json()['data'])}")

    rows.append("\n=== UPLOAD  what the 201 says, and when the field stops being a placeholder")
    init = c.get(f"/entity/versions/{vid}/image/_upload",
                 params={"filename": "probe024.png"}).json()
    requests.put(init["links"]["upload"], data=PNG, timeout=60)
    cr = c.post(init["links"]["complete_upload"],
                json={"upload_info": init["data"], "upload_data": {}})
    rows.append(f"  POST complete_upload -> {cr.status_code}, body {len(cr.content)}b {cr.text!r}")

    t0 = time.time()
    for wait in (0, 2, 3, 5, 10, 20, 30, 60):
        time.sleep(wait)
        img = c.get(f"/entity/versions/{vid}",
                    params={"fields": "image"}).json()["data"]["attributes"]["image"]
        placeholder = "/images/status/transient/" in (img or "")
        rows.append(f"    t+{time.time() - t0:>5.1f}s  placeholder={placeholder}  "
                    f"{(img or 'null').split('?')[0]}")
        if img and not placeholder:
            break

    rows.append("\n=== DELETE  what it returns")
    tmp = c.post("/entity/versions", json=body("zzprobe_024_del")).json()["data"]["id"]
    dr = c.delete(f"/entity/versions/{tmp}")
    rows.append(f"  DELETE /entity/versions/{{id}} -> {dr.status_code}, body {len(dr.content)}b "
                f"{dr.text!r}")
    rows.append(f"  GET the deleted id           -> {c.get(f'/entity/versions/{tmp}').status_code}")

_lib.emit("024_read_after_write", "\n".join(rows), env)
