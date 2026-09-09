"""Q: is `name` in an entity dict the target's display name for every type it can hold?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []
J = {"Content-Type": "application/json"}
ARR = "application/vnd+shotgun.api3_array+json"
HSH = "application/vnd+shotgun.api3_hash+json"
IDENT = ("code", "content", "name", "subject", "title")
# Two types hold more than one of them and the first is not the name a person reads.
OVERRIDE = {"Note": "subject", "Project": "name"}
TAG = "zzprobe_060"


def detail(r):
    try:
        e = r.json().get("errors", [{}])[0]
        return json.dumps({k: e.get(k) for k in ("title", "detail") if e.get(k)})
    except Exception:
        return r.text[:200]


vt = c.get("/schema/Version/fields/entity").json()["data"]["properties"]["valid_types"]["value"]
rows.append(f"Version.entity valid_types ({len(vt)}): {', '.join(vt)}")

targets = list(vt) + ["Task", "Note", "Project"]
info = {}
rows.append("")
rows.append(f"  {'type':<18} {'identity fields':<28} {'cached_display_name':<20} project field")
for t in targets:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        info[t] = None
        rows.append(f"  {t:<18} GET /schema/{t}/fields -> {r.status_code}")
        continue
    f = r.json()["data"]
    _lib.note_from({k: (v.get("name") or {}).get("value") for k, v in f.items()})
    present = [k for k in IDENT if k in f]
    info[t] = {"ident": present, "idf": OVERRIDE.get(t) or (present[0] if present else None),
               "cdn": "cached_display_name" in f, "project": "project" in f}
    rows.append(f"  {t:<18} {', '.join(present) or 'none':<28} "
                f"{str(info[t]['cdn']):<20} {info[t]['project']}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write)")
    _lib.emit("060_entity_dict_name", "\n".join(rows), env)
    raise SystemExit(0)

pid = _lib.sandbox_id(c, env)
with _lib.Created(c) as made:
    v = c.post("/entity/versions", headers=J,
               json={"project": {"type": "Project", "id": pid}, "code": f"{TAG}_carrier"})
    vid = made.add("versions", v.json()["data"]["id"])

    # One row per target type, created where the API takes a minimal create.
    made_targets = {}
    rows.append("\ncreate one row per type in the sandbox")
    for t in targets:
        if t == "Project":
            made_targets[t] = (pid, "name")          # the sandbox project itself; never created
            rows.append(f"  {t:<18} the sandbox project, not created")
            continue
        i = info.get(t)
        if not i:
            continue
        idf = i["idf"]
        body = {}
        if i["project"]:
            body["project"] = {"type": "Project", "id": pid}
        if idf:
            body[idf] = f"{TAG}_{t.lower()}"
        r = c.post(f"/entity/{t}", json=body, headers=J)
        if not r.ok:
            rows.append(f"  {t:<18} POST /entity/{t} -> {r.status_code} {detail(r)}")
            continue
        made_targets[t] = (made.add(t, r.json()["data"]["id"]), idf)
        rows.append(f"  {t:<18} POST /entity/{t} -> {r.status_code} id={made_targets[t][0]}")

    # 1. link each one through Version.entity and read the dict back
    rows.append("\nVersion.entity, one PUT per type, read back with GET /entity/versions/<id>")
    rows.append(f"  {'type':<18} {'PUT':<5} {'dict keys':<22} {'dict name':<26} "
                f"{'identity field/value':<34} cached_display_name")
    for t, (rid, idf) in made_targets.items():
        want = ",".join(sorted({x for x in (idf, "cached_display_name") if x}))
        a = c.get(f"/entity/{t}/{rid}", params={"fields": want}).json()["data"]["attributes"]
        _lib.note_from(a)
        p = c.put(f"/entity/versions/{vid}", json={"entity": {"type": t, "id": rid}}, headers=J)
        if not p.ok:
            rows.append(f"  {t:<18} {p.status_code:<5} {detail(p)}")
            continue
        d = c.get(f"/entity/versions/{vid}").json()["data"]["relationships"]["entity"]["data"]
        _lib.note_from(d)
        rows.append(f"  {t:<18} {p.status_code:<5} {','.join(sorted(d or {})):<22} "
                    f"{json.dumps((d or {}).get('name')):<26} "
                    f"{idf}={json.dumps(a.get(idf)):<32} {json.dumps(a.get('cached_display_name'))}")

    # the typed fields a client would actually use for the types Version.entity does not name
    rows.append("\nthe same targets through their own field")
    if "Task" in made_targets:
        c.put(f"/entity/versions/{vid}", headers=J,
              json={"sg_task": {"type": "Task", "id": made_targets["Task"][0]}})
    got = c.get(f"/entity/versions/{vid}").json()["data"]["relationships"]
    for f in ("sg_task", "project", "user", "created_by"):
        if f in got:
            _lib.note_from(got[f]["data"])
            rows.append(f"  {f:<18} {json.dumps(got[f]['data'])}")

    # 2. both _search vendor Content-Types, against the GET
    rows.append("\nsame row, three ways")
    g = c.get(f"/entity/versions/{vid}", params={"fields": "entity,sg_task,project"}).json()["data"]
    a = c.post("/entity/versions/_search", headers={"Content-Type": ARR},
               data=json.dumps({"filters": [["id", "is", vid]], "fields": "entity,sg_task,project"}))
    h = c.post("/entity/versions/_search", headers={"Content-Type": HSH},
               data=json.dumps({"filters": {"logical_operator": "and",
                                            "conditions": [["id", "is", vid]]},
                                "fields": "entity,sg_task,project"}))
    shapes = {}
    for label, obj in (("GET", g), (f"_search {ARR}", a.json()["data"][0] if a.ok else None),
                       (f"_search {HSH}", h.json()["data"][0] if h.ok else None)):
        shapes[label] = json.dumps((obj or {}).get("relationships", {}), sort_keys=True)
        rows.append(f"  {label}: {shapes[label][:240]}")
    rows.append(f"  all three identical: {len(set(shapes.values())) == 1}")

    # 3. multi_entity elements
    rows.append("\nmulti_entity elements")
    v2 = c.post("/entity/versions", headers=J,
                json={"project": {"type": "Project", "id": pid}, "code": f"{TAG}_source"})
    v2id = made.add("versions", v2.json()["data"]["id"])
    multi = [("sg_ai_generated_from", "Version", v2id)]
    for f, t in (("notes", "Note"), ("tasks", "Task")):
        if t in made_targets:
            multi.append((f, t, made_targets[t][0]))
    pl = c.post("/entity/Playlist", headers=J,
                json={"project": {"type": "Project", "id": pid}, "code": f"{TAG}_playlist"})
    if pl.ok:
        multi.append(("playlists", "Playlist", made.add("Playlist", pl.json()["data"]["id"])))
    else:
        rows.append(f"  POST /entity/Playlist -> {pl.status_code} {detail(pl)}")
    for f, t, rid in multi:
        p = c.put(f"/entity/versions/{vid}", json={f: [{"type": t, "id": rid}]}, headers=J)
        if not p.ok:
            rows.append(f"  {f:<24} PUT {p.status_code} {detail(p)}")
            continue
        d = c.get(f"/entity/versions/{vid}").json()["data"]["relationships"][f]["data"]
        _lib.note_from(d)
        rows.append(f"  {f:<24} PUT {p.status_code} {json.dumps(d)}")

    # 4. is cached_display_name readable, and does it equal the dict name?
    rows.append("\ncached_display_name and the identity field, asked for directly")
    rows.append(f"  {'type':<18} {'GET ?fields=cached_display_name':<44} "
                f"{'_search fields=cached_display_name':<44} ?fields=name")
    for t in ("Task", "Shot", "Asset", "Project", "Version", "Note"):
        rid = made_targets.get(t, (None, None))[0] or (vid if t == "Version" else None)
        if not rid:
            continue
        g1 = c.get(f"/entity/{t}/{rid}", params={"fields": "cached_display_name"})
        one = g1.json()["data"]["attributes"] if g1.ok else f"<{g1.status_code}>"
        s1 = c.post(f"/entity/{t}/_search", headers={"Content-Type": ARR},
                    data=json.dumps({"filters": [["id", "is", rid]],
                                     "fields": "cached_display_name"}))
        two = (s1.json()["data"][0]["attributes"] if s1.ok and s1.json()["data"]
               else f"<{s1.status_code}>")
        g2 = c.get(f"/entity/{t}/{rid}", params={"fields": "name"})
        three = g2.json()["data"]["attributes"] if g2.ok else f"<{g2.status_code}>"
        _lib.note_from(one)
        rows.append(f"  {t:<18} {json.dumps(one):<44} {json.dumps(two):<44} {json.dumps(three)}")
    for t, f in (("Task", "name"), ("Task", "code"), ("Task", "cached_display_name"),
                 ("Note", "name"), ("Version", "name")):
        r = c.post(f"/entity/{t}/_search", headers={"Content-Type": ARR},
                   data=json.dumps({"filters": [[f, "is", "x"]], "fields": "id"}))
        rows.append(f"  filter {t}.{f} -> {r.status_code} {detail(r) if not r.ok else 'ok'}")

    # 5. what the dict holds once the target is gone
    rows.append("\ndeleted target")

    def gone(slug, rid):
        """Delete a row and stop the exit handler deleting it a second time."""
        r = c.delete(f"/entity/{slug}/{rid}")
        if (slug, rid) in made.rows:
            made.rows.remove((slug, rid))
        return r.status_code

    def carrier(code):
        r = c.post("/entity/versions", headers=J,
                   json={"project": {"type": "Project", "id": pid}, "code": f"{TAG}_{code}"})
        return made.add("versions", r.json()["data"]["id"])

    def rel(holder, field):
        r = c.get(f"/entity/versions/{holder}")
        if not r.ok:
            return f"GET /entity/versions/{holder} -> {r.status_code}"
        return json.dumps(r.json()["data"]["relationships"][field]["data"])

    cases = [("entity", "Shot", {"project": {"type": "Project", "id": pid},
                                 "code": f"{TAG}_doomed_shot"}),
             ("sg_task", "Task", {"project": {"type": "Project", "id": pid},
                                  "content": f"{TAG}_doomed_task"}),
             ("playlists", "Playlist", {"project": {"type": "Project", "id": pid},
                                        "code": f"{TAG}_doomed_playlist"})]
    for field, t, body in cases:
        holder = carrier(f"holder_{field}")
        r = c.post(f"/entity/{t}", json=body, headers=J)
        rid = made.add(t, r.json()["data"]["id"])
        value = [{"type": t, "id": rid}] if field == "playlists" else {"type": t, "id": rid}
        c.put(f"/entity/versions/{holder}", json={field: value}, headers=J)
        rows.append(f"  {field:<10} before: {rel(holder, field)}")
        rows.append(f"  {field:<10} DELETE /entity/{t}/{rid} -> {gone(t, rid)}")
        rows.append(f"  {field:<10} after:  {rel(holder, field)}")
        rr = c.get(f"/entity/versions/{holder}", params={"options[return_only]": "retired"})
        rows.append(f"  {field:<10} the holder as retired: {rr.status_code} "
                    f"{json.dumps(rr.json()['data']['relationships'][field]['data']) if rr.ok else ''}")
        sr = c.post("/entity/versions/_search", headers={"Content-Type": ARR},
                    data=json.dumps({"filters": [["id", "is", holder]], "fields": field}))
        seen = sr.json()["data"] if sr.ok else []
        rows.append(f"  {field:<10} _search: {sr.status_code} "
                    f"{json.dumps(seen[0]['relationships']) if seen else '0 rows'}")
        nf = c.post("/entity/versions/_search", headers={"Content-Type": ARR},
                    data=json.dumps({"filters": [[field, "is", {"type": t, "id": rid}]],
                                     "fields": "id"}))
        rows.append(f"  {field:<10} filter {field} is the deleted row -> {nf.status_code} "
                    f"{len(nf.json()['data']) if nf.ok else detail(nf)} rows")

_lib.emit("060_entity_dict_name", "\n".join(rows), env)
