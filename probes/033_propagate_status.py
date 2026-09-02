"""Q: how is a status propagated from Tasks and Versions up to the entity that owns them, without
racing a concurrent write?

A survey of production code found about fourteen implementations of this one pattern across five
repositories. All of them re-query the full sibling set rather than trusting the row that triggered
them, and all of them re-read the trigger immediately before writing the parent. Neither habit is
documented. This probe walks the whole loop once and measures what the API does and does not offer:
the usable status vocabulary, the one-call sibling query, the re-read guard, and whether
POST /entity/_batch collapses the write half.
"""
import json
import time

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []


def prop(p, key, default=None):
    """Schema properties are wrapped as {"value": x, "editable": bool}."""
    return (p.get(key) or {}).get("value", default)


def vocabulary(entity_type, project_id, field="sg_status_list"):
    """valid_values minus hidden_values, per project (probe 009). The API enforces neither subtraction."""
    d = c.get(f"/schema/{entity_type}/fields/{field}", params={"project_id": project_id}).json()["data"]
    p = d.get("properties", {})
    valid = prop(p, "valid_values", []) or []
    hidden = prop(p, "hidden_values", []) or []
    return {"valid": valid, "hidden": hidden,
            "usable": [v for v in valid if v not in hidden],
            "labels": prop(p, "display_values", {}) or {},
            "default": prop(p, "default_value")}


def siblings(slug, parent_type, parent_id, fields):
    """Every child of one parent in one call. `entity` is the owning link on both Task and Version."""
    r = c.post(f"/entity/{slug}/_search", headers=ARR, json={
        "filters": [["entity", "is", {"type": parent_type, "id": parent_id}]],
        "fields": fields, "page": {"size": 500}})
    if not r.ok:
        return r.status_code, r.json().get("errors", r.json())
    _lib.note_from(r.json())
    return r.status_code, r.json()["data"]


def status_of(slug, entity_id):
    d = c.get(f"/entity/{slug}/{entity_id}", params={"fields": "sg_status_list"}).json()["data"]
    return d["attributes"]["sg_status_list"]


# ---------------------------------------------------------------- vocabulary, read-only
SAMPLE = _lib.sample_projects(c, env)[0]
task_v = vocabulary("Task", SAMPLE)
shot_v = vocabulary("Shot", SAMPLE)

rows.append("=== 1. usable vocabulary, per project (probe 009)")
rows.append(f"  Task  valid={task_v['valid']}")
rows.append(f"        hidden={task_v['hidden']}  usable={task_v['usable']}  default={task_v['default']!r}")
rows.append(f"  Shot  valid={shot_v['valid']}")
rows.append(f"        hidden={shot_v['hidden']}  usable={shot_v['usable']}  default={shot_v['default']!r}")

# "every status except these" is the variant that forces the schema read: the blocking set is whatever
# the project has that is not a finished code, so it grows when the site adds a status.
DONE_PREF = ["fin", "cmpt", "apr", "omt", "na"]
task_done = [s for s in DONE_PREF if s in task_v["usable"]]
task_blocking = [s for s in task_v["usable"] if s not in task_done]
shot_done = next((s for s in ["fin", "cmpt", "apr"] if s in shot_v["usable"]), shot_v["usable"][-1])
shot_wip = next((s for s in ["ip", "rev", "wtg"] if s in shot_v["usable"]), shot_v["usable"][0])
rows.append(f"  derived: Task done={task_done}")
rows.append(f"           Task blocking (usable minus done, {len(task_blocking)} codes)={task_blocking}")
rows.append(f"           Shot target when every sibling is done={shot_done!r}, otherwise {shot_wip!r}")
rows.append(f"  labels are not codes: {json.dumps({k: task_v['labels'].get(k) for k in task_done})}")

# ---------------------------------------------------------------- the sibling query, read-only
rows.append("\n=== 2. the sibling query, on a read-only project")
r = c.post("/entity/tasks/_search", headers=ARR, json={
    "filters": [["project", "is", {"type": "Project", "id": SAMPLE}], ["entity", "is_not", None]],
    "fields": ["content", "sg_status_list", "entity"], "page": {"size": 1}})
_lib.note_from(r.json())
seed = r.json()["data"][0] if r.ok and r.json()["data"] else None
if seed:
    par = seed["relationships"]["entity"]["data"]
    code, sib = siblings("tasks", par["type"], par["id"], ["content", "sg_status_list"])
    rows.append(f"  POST /entity/tasks/_search  filters=[['entity','is',{{'type': '{par['type']}',"
                f" 'id': {par['id']}}}]]  -> {code}, {len(sib)} rows in one call")
    rows.append("    " + json.dumps([s["attributes"]["sg_status_list"] for s in sib]))
    code, vsib = siblings("versions", par["type"], par["id"], ["code", "sg_status_list"])
    rows.append(f"  the same filter on /entity/versions/_search -> {code}, "
                f"{len(vsib) if isinstance(vsib, list) else vsib} rows")

    # Many parents at once, which is what makes a batched write worth having.
    for label, flt in (("entity in [hash, hash]", [["entity", "in", [par, par]]]),
                       ("entity.<Type>.id in [id]", [[f"entity.{par['type']}.id", "in", [par["id"]]]])):
        r = c.post("/entity/tasks/_search", headers=ARR,
                   json={"filters": flt, "fields": ["content"], "page": {"size": 500}})
        got = len(r.json()["data"]) if r.ok else json.dumps(r.json()["errors"])
        rows.append(f"  multi-parent  {label:<24} -> {r.status_code}, {got}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; the propagation walk needs --write)")
    _lib.emit("033_propagate_status", "\n".join(rows), env)
    raise SystemExit(0)

# ---------------------------------------------------------------- the walk, in the sandbox
SANDBOX = _lib.sandbox_id(c, env)
task_v = vocabulary("Task", SANDBOX)
shot_v = vocabulary("Shot", SANDBOX)
task_done = [s for s in DONE_PREF if s in task_v["usable"]]
task_blocking = [s for s in task_v["usable"] if s not in task_done]
shot_done = next((s for s in ["fin", "cmpt", "apr"] if s in shot_v["usable"]), shot_v["usable"][-1])
shot_wip = next((s for s in ["ip", "rev", "wtg"] if s in shot_v["usable"]), shot_v["usable"][0])
rows.append(f"\n=== 3. sandbox project {SANDBOX}: Task usable={task_v['usable']}")
rows.append(f"    Task hidden={task_v['hidden']}  done={task_done}  blocking={task_blocking}")
rows.append(f"    Shot usable={shot_v['usable']}  done={shot_done!r}  wip={shot_wip!r}")

DONE, WIP = task_done[0], task_blocking[0]

with _lib.Created(c) as made:
    shots = {}
    for tag in ("a", "b"):
        sid = made.add("shots", c.post("/entity/shots", json={
            "project": {"type": "Project", "id": SANDBOX},
            "code": f"zzprobe_033_sh_{tag}", "sg_status_list": shot_wip}).json()["data"]["id"])
        shots[tag] = sid
    tasks = {}
    for tag, sid in shots.items():
        tasks[tag] = [made.add("tasks", c.post("/entity/tasks", json={
            "project": {"type": "Project", "id": SANDBOX},
            "entity": {"type": "Shot", "id": sid},
            "content": f"zzprobe_033_{tag}_{n}", "sg_status_list": DONE}).json()["data"]["id"])
            for n in range(3)]
    # Shot a is one Task short of done; shot b is done. The trigger is the last Task on shot a.
    trigger = tasks["a"][-1]
    c.put(f"/entity/tasks/{trigger}", json={"sg_status_list": WIP})
    rows.append(f"    shot a tasks {tasks['a']} statuses "
                f"{[status_of('tasks', t) for t in tasks['a']]}")
    rows.append(f"    shot b tasks {tasks['b']} statuses "
                f"{[status_of('tasks', t) for t in tasks['b']]}")

    # Versions hang off the same `entity` link, with their own vocabulary. There is no one search
    # that returns both child types, so a rule over both is two calls.
    ver_v = vocabulary("Version", SANDBOX)
    ver_wip = next((s for s in ["rev", "ip", "wtg"] if s in ver_v["usable"]), ver_v["usable"][0])
    vid = made.add("versions", c.post("/entity/versions", json={
        "project": {"type": "Project", "id": SANDBOX}, "entity": {"type": "Shot", "id": shots["b"]},
        "code": "zzprobe_033_v001", "sg_status_list": ver_wip}).json()["data"]["id"])
    code, vsib = siblings("versions", "Shot", shots["b"], ["code", "sg_status_list"])
    rows.append(f"    Version usable={ver_v['usable']}")
    rows.append(f"    one Version on shot b -> the same filter on /entity/versions/_search returns "
                f"{[s['attributes']['sg_status_list'] for s in vsib]}")

    rows.append("\n=== 4. decide from all siblings, never from the row that triggered")
    ver_done = [s for s in DONE_PREF if s in ver_v["usable"]]
    decisions = {}
    for tag, sid in shots.items():
        code, sib = siblings("tasks", "Shot", sid, ["content", "sg_status_list"])
        got = [s["attributes"]["sg_status_list"] for s in sib]
        code, vsib = siblings("versions", "Shot", sid, ["code", "sg_status_list"])
        vgot = [s["attributes"]["sg_status_list"] for s in vsib]
        done = bool(got) and all(s in task_done for s in got) and all(s in ver_done for s in vgot)
        want = shot_done if done else shot_wip
        decisions[tag] = want
        rows.append(f"  shot {tag}  tasks {got}  versions {vgot}  "
                    f"not done: {[s for s in got + vgot if s not in task_done + ver_done]}  -> {want!r}")
    rows.append(f"  the trigger alone said {status_of('tasks', trigger)!r}; shot a is still {decisions['a']!r}")

    rows.append("\n=== 5. is there a server-side guard? conditional-write headers on PUT")
    g = c.get(f"/entity/tasks/{trigger}", params={"fields": "sg_status_list,updated_at"})
    hdr = {k: v for k, v in g.headers.items()
           if k.lower() in ("etag", "last-modified", "cache-control", "vary")}
    rows.append(f"  GET response headers of interest: {json.dumps(hdr)}")
    stamp = g.json()["data"]["attributes"].get("updated_at")
    for label, headers in (("If-Match: \"zzstale\"", {"If-Match": '"zzstale"'}),
                           ("If-Unmodified-Since: 1990", {"If-Unmodified-Since": "Mon, 01 Jan 1990 00:00:00 GMT"}),
                           ("If-None-Match: *", {"If-None-Match": "*"})):
        r = c.put(f"/entity/tasks/{trigger}", headers=headers, json={"sg_status_list": WIP})
        rows.append(f"  PUT {label:<34} -> {r.status_code} "
                    f"{'applied' if r.ok else json.dumps(r.json().get('errors'))}")
    r = c.put(f"/entity/tasks/{trigger}", json={"sg_status_list": WIP, "updated_at": stamp})
    rows.append(f"  PUT updated_at echoed back in the body      -> {r.status_code} "
                f"{'' if r.ok else json.dumps(r.json().get('errors'))}")

    rows.append("\n=== 6. the client-side guard: re-read the trigger, compare, abandon")
    before = status_of("tasks", trigger)
    c.put(f"/entity/tasks/{trigger}", json={"sg_status_list": DONE})   # a concurrent writer
    now = status_of("tasks", trigger)
    rows.append(f"  decided on {before!r}; re-read immediately before the write says {now!r}")
    rows.append(f"  guard: {before!r} != {now!r} -> abandon, recompute. The parent is untouched: "
                f"{status_of('shots', shots['a'])!r}")

    code, sib = siblings("tasks", "Shot", shots["a"], ["content", "sg_status_list"])
    got = [s["attributes"]["sg_status_list"] for s in sib]
    decisions["a"] = shot_done if all(s in task_done for s in got) else shot_wip
    rows.append(f"  recomputed from all siblings {got} -> shot a {decisions['a']!r}")
    again = status_of("tasks", trigger)
    rows.append(f"  second guard: {now!r} == {again!r} -> proceed")

    rows.append("\n=== 7. write the parents, one batch (probe 024, recipe 002)")
    reqs = [{"request_type": "update", "entity": "Shot", "record_id": shots[t],
             "data": {"sg_status_list": decisions[t]}} for t in ("a", "b")]
    t0 = time.time()
    r = c.post("/entity/_batch", json={"requests": reqs})
    batch_ms = (time.time() - t0) * 1000
    rows.append(f"  POST /entity/_batch  {len(reqs)} updates -> {r.status_code} in {batch_ms:.0f}ms")
    if r.ok:
        for req, row in zip(reqs, r.json()["data"]):
            d = row.get("data", row)
            rows.append(f"    {req['entity']} {d['id']} sg_status_list in the response: "
                        f"{d['attributes']['sg_status_list']!r}")
    else:
        rows.append(f"    {json.dumps(r.json().get('errors'))}")
    t0 = time.time()
    for t in ("a", "b"):
        c.put(f"/entity/shots/{shots[t]}", json={"sg_status_list": decisions[t]})
    rows.append(f"  the same two writes as individual PUTs -> {(time.time() - t0) * 1000:.0f}ms")

    rows.append("\n=== 8. verify by re-reading (probe 028)")
    for t in ("a", "b"):
        rows.append(f"  shot {t}  wanted {decisions[t]!r}  reads back {status_of('shots', shots[t])!r}")

    rows.append("\n=== 9. what a client must subtract itself")
    stray = [h for h in task_v["hidden"] if h not in task_v["valid"]]
    if stray:
        r = c.put(f"/entity/tasks/{trigger}", json={"sg_status_list": stray[0]})
        rows.append(f"  hidden_values names {stray}, absent from valid_values; PUT {stray[0]!r} "
                    f"-> {r.status_code}")
    hidden = next((h for h in task_v["hidden"] if h in task_v["valid"]), None)
    if hidden:
        r = c.put(f"/entity/tasks/{trigger}", json={"sg_status_list": hidden})
        rows.append(f"  PUT a project-hidden Task status {hidden!r} -> {r.status_code}, "
                    f"reads back {status_of('tasks', trigger)!r}")
        code, sib = siblings("tasks", "Shot", shots["a"], ["content", "sg_status_list"])
        seen = [s["attributes"]["sg_status_list"] for s in sib]
        rows.append(f"  the sibling query returns it like any other code: {seen}")
        by_done = all(s in task_done for s in seen)
        by_block = not any(s in task_blocking for s in seen)
        rows.append(f"  all(s in done)         -> {by_done}  shot {shot_done if by_done else shot_wip!r}")
        rows.append(f"  not any(s in blocking) -> {by_block}  shot {shot_done if by_block else shot_wip!r}"
                    f"   blocking was built from usable, and {hidden!r} is not in it")
    else:
        rows.append("  the sandbox project hides nothing on Task, so there is no hidden code to write")
    label = task_v["labels"].get(DONE, DONE)
    r = c.put(f"/entity/tasks/{trigger}", json={"sg_status_list": label})
    rows.append(f"  PUT the display label {label!r} instead of {DONE!r} -> {r.status_code} "
                f"{json.dumps(r.json().get('errors')) if not r.ok else 'applied'}")
    r = c.post("/entity/tasks/_search", headers=ARR, json={
        "filters": [["entity", "is", {"type": "Shot", "id": shots["a"]}],
                    ["sg_status_list", "is", label]], "fields": ["content"]})
    rows.append(f"  the same label in a filter -> {r.status_code}, "
                f"{len(r.json()['data']) if r.ok else json.dumps(r.json()['errors'])} rows")

_lib.emit("033_propagate_status", "\n".join(rows), env)
