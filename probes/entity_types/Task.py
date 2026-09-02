"""Q: how is a Task addressed, created, linked, scheduled and sequenced over REST?

Task is the type a client gets wrong first: its identity field is `content`, not the `code` almost
everything else uses. The create contract, what a Task hangs off (`entity` and `step`), the scheduling
block (`start_date`, `due_date`, `duration`, `time_logs_sum`, `time_vs_est`) and whether the Gantt
dependency fields are exposed over REST are all measured here.

Read-only against the first sample project. Writes go into the sandbox behind --write and are deleted.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
SLUG = "tasks"
rows = []


def errs(r):
    """The whole errors[] object, `source` included. The 400 is the documentation (probe 017)."""
    try:
        return json.dumps(r.json().get("errors"), indent=1)
    except ValueError:
        return r.text


def flat(r, n=400):
    return errs(r).replace("\n", " ")[:n]


def search(entity, filters, fields, size=200):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": list(filters), "fields": list(fields), "page": {"size": size}})
    return (r.json()["data"], None) if r.ok else (None, r)


def count(label, filters, fields=("content",)):
    data, bad = search(SLUG, filters, fields)
    if bad is not None:
        rows.append(f"  {label:<52} -> {bad.status_code} {json.loads(errs(bad))[0].get('title')}")
        return None
    rows.append(f"  {label:<52} -> {len(data)}")
    return data


def rel(d):
    return {k: (v or {}).get("data") for k, v in (d.get("relationships") or {}).items()}


P = _lib.sample_projects(c, env)[0]
PROJ = ["project", "is", {"type": "Project", "id": P}]

# ---------------------------------------------------------------- path and scope
rows.append("=== path slug")
for path in ("/entity/tasks", "/entity/task", "/entity/Task"):
    r = c.get(path, params={"page[size]": 1, "fields": "content"})
    body = r.json()
    rows.append(f"  GET {path:<16} -> {r.status_code} " + (
        f"data[0].type={body['data'][0]['type']!r} self={body['data'][0]['links']['self']!r}"
        if r.ok else flat(r, 240)))
r = c.get("/entity/zzznope", params={"page[size]": 1})
rows.append(f"  GET /entity/zzznope   -> {r.status_code} {flat(r, 200)}")

sch = c.get("/schema/Task/fields").json()["data"]
rows.append(f"\n=== schema: {len(sch)} fields on Task")
val = lambda f, k, d="": (sch[f].get(k) or {}).get("value", d)  # noqa: E731
vt = lambda f: ((sch[f].get("properties") or {}).get("valid_types") or {}).get("value", "")  # noqa: E731
rows.append("  field                     data_type      editable mandatory valid_types")
for f in ("content", "cached_display_name", "project", "entity", "step", "sg_status_list",
          "start_date", "due_date", "duration", "est_in_mins", "time_logs_sum", "time_vs_est",
          "time_percent_of_est", "upstream_tasks", "downstream_tasks", "sibling_tasks",
          "dependency_violation", "pinned", "milestone", "splits", "split_durations",
          "task_assignees", "color", "sg_sort_order", "template_task", "task_template"):
    rows.append(f"  {f:<25} {val(f, 'data_type'):<14} {str(val(f, 'editable')):<8} "
                f"{str(val(f, 'mandatory')):<9} {vt(f)}")
for absent in ("code", "name", "sg_task_name"):
    rows.append(f"  {absent:<25} present in schema: {absent in sch}")

# ---------------------------------------------------------------- identity
rows.append("\n=== identity: what a Task is called")
data, _ = search(SLUG, [PROJ], ("content", "cached_display_name", "code", "name",
                                "entity", "step", "sg_status_list"), size=3)
if data:
    _lib.note_from(data)
    for row in data:
        rows.append(f"  id={row['id']} attributes={json.dumps(row['attributes'])}")
    rows.append(f"  relationships={json.dumps(data[0].get('relationships'))}")

rows.append("\n=== filtering on the field a client guesses")
one = (data or [{}])[0].get("attributes", {}).get("content")
count(f"content is {one!r}", [PROJ, ["content", "is", one]])
count(f"code is {one!r}", [PROJ, ["code", "is", one]])
count(f"name is {one!r}", [PROJ, ["name", "is", one]])
count(f"cached_display_name is {one!r}", [PROJ, ["cached_display_name", "is", one]])
count("content is 'zzprobe_nope'", [PROJ, ["content", "is", "zzprobe_nope"]])

# ---------------------------------------------------------------- links
rows.append("\n=== what a Task hangs off")
for f, v in sorted(sch.items()):
    dt = (v.get("data_type") or {}).get("value")
    if dt in ("entity", "multi_entity"):
        rows.append(f"  {f:<22} {dt:<13} editable={str((v.get('editable') or {}).get('value')):<5} "
                    f"{str(vt(f))[:200]}")

rows.append("\n=== which link a client filters on")
data, _ = search(SLUG, [PROJ, ["entity", "type_is", "Shot"]], ("content", "entity"), size=1)
shot = (data or [{}])[0].get("relationships", {}).get("entity", {}).get("data")
if shot:
    _lib.note_from(shot)
    count(f"entity is {{Shot,{shot['id']}}}", [PROJ, ["entity", "is", {"type": "Shot", "id": shot["id"]}]])
    count(f"entity.Shot.code is {shot['name']!r}", [PROJ, ["entity.Shot.code", "is", shot["name"]]])
count("entity type_is Shot", [PROJ, ["entity", "type_is", "Shot"]])
count("entity type_is Asset", [PROJ, ["entity", "type_is", "Asset"]])
count("entity is None", [PROJ, ["entity", "is", None]])
d, _ = search(SLUG, [PROJ, ["step", "is_not", None]], ("content", "step"), size=1)
st = (d or [{}])[0].get("relationships", {}).get("step", {}).get("data")
steps, _ = search("steps", [["id", "is", st["id"]]] if st else [],
                  ("code", "short_name", "entity_type"), size=1)
if st and steps:
    _lib.note_from(steps)
    rows.append(f"  Step {steps[0]['id']}: {json.dumps(steps[0]['attributes'])}")
    count(f"step is {{Step,{st['id']}}}", [PROJ, ["step", "is", {"type": "Step", "id": st["id"]}]])
    count(f"step.Step.short_name is {steps[0]['attributes']['short_name']!r}",
          [PROJ, ["step.Step.short_name", "is", steps[0]["attributes"]["short_name"]]])
    count("step.Step.short_name is 'ZZNOPE'", [PROJ, ["step.Step.short_name", "is", "ZZNOPE"]])

# ---------------------------------------------------------------- scheduling
rows.append("\n=== scheduling, read side (field_types/duration for the unit)")
r = c.get("/preferences")
pref = r.json()["data"] if r.ok else {}
rows.append(f"  GET /preferences -> {r.status_code} hours_per_day={json.dumps(pref.get('hours_per_day'))} "
            f"duration_units={json.dumps(pref.get('duration_units'))}")
data, _ = search(SLUG, [PROJ, ["duration", "is_not", None]],
                 ("content", "start_date", "due_date", "duration", "est_in_mins",
                  "time_logs_sum", "time_vs_est", "time_percent_of_est"), size=3)
for row in data or []:
    a = row["attributes"]
    rows.append("  " + " ".join(f"{k}={a.get(k)!r}" for k in
                                ("start_date", "due_date", "duration", "est_in_mins",
                                 "time_logs_sum", "time_vs_est", "time_percent_of_est")))

# ---------------------------------------------------------------- dependencies, read side
rows.append("\n=== dependencies over REST, read side")
for f in ("upstream_tasks", "downstream_tasks", "sibling_tasks"):
    d, bad = search(SLUG, [PROJ, [f, "is_not", None]], ("content", f), size=200)
    rows.append(f"  filter {f:<17} is_not None -> "
                + (f"{len(d)} rows" if bad is None else f"{bad.status_code} {flat(bad, 200)}"))
d, bad = search(SLUG, [PROJ], ("content", "upstream_tasks.Task.content"), size=1)
rows.append("  dotted read upstream_tasks.Task.content -> "
            + (json.dumps(d[0]["attributes"]) if d else f"{bad.status_code} {flat(bad, 200)}"))

rows.append("\n=== TaskDependency, the join entity")
dep = c.get("/schema/TaskDependency/fields")
rows.append(f"  GET /schema/TaskDependency/fields -> {dep.status_code}")
if dep.ok:
    ds = dep.json()["data"]
    for f, v in sorted(ds.items()):
        vts = ((v.get("properties") or {}).get("valid_types") or {}).get("value", "")
        rows.append(f"  {f:<20} {(v.get('data_type') or {}).get('value'):<13} "
                    f"editable={str((v.get('editable') or {}).get('value')):<5} {vts}")
    rows.append(f"  project field present: {'project' in ds}")
    r = c.get("/entity/task_dependencies", params={"page[size]": 2})
    rows.append(f"  GET /entity/task_dependencies (no ?fields) -> {r.status_code} "
                f"{json.dumps((r.json().get('data') or [{}])[0])[:160]}")
    r = c.get("/entity/task_dependencies", params={"page[size]": 2, "fields": ",".join(sorted(ds))})
    rows.append(f"  GET /entity/task_dependencies?fields=<all> -> {r.status_code}")
    for row in (r.json().get("data") or []) if r.ok else []:
        _lib.note_from(row)
        rows.append(f"    id={row['id']} attributes={json.dumps(row['attributes'])}")
        rows.append(f"      relationships={json.dumps(rel(row))[:240]}")
    side = (rel((r.json().get("data") or [{}])[0]).get("task") or {}) if r.ok else {}
    if side:
        t = c.get(f"/entity/tasks/{side['id']}", params={
            "fields": "content,upstream_tasks,downstream_tasks,sibling_tasks,dependency_violation"})
        d = t.json()["data"] if t.ok else {}
        _lib.note_from(d)
        rows.append(f"    the same link read off the Task: attributes={json.dumps(d.get('attributes'))}")
        rows.append(f"      relationships={json.dumps(rel(d))[:400]}")

# ---------------------------------------------------------------- status
rows.append("\n=== status: which field, and how a project's usable set is read")
site = c.get("/schema/Task/fields/sg_status_list").json()["data"]["properties"]
proj = c.get("/schema/Task/fields/sg_status_list",
             params={"project_id": P}).json()["data"]["properties"]
rows.append(f"  properties keys: {sorted(site)}")
for k in ("valid_values", "hidden_values", "display_values", "default_value"):
    rows.append(f"  site    {k:<15} = {json.dumps((site.get(k) or {}).get('value'))[:200]}")
    rows.append(f"  project {k:<15} = {json.dumps((proj.get(k) or {}).get('value'))[:200]}")

if not _lib.writes_allowed():
    rows.append("\n(no --write: create, scheduling writes and dependency writes skipped)")
    _lib.emit("entity_types/Task", "\n".join(rows), env)
    raise SystemExit

# ---------------------------------------------------------------- writes
S = _lib.sandbox_id(c, env)
SP = {"type": "Project", "id": S}
rows.append("\n=== create contract, sandbox project (probe 012: mandatory is not the contract)")
with _lib.Created(c) as made:
    r = c.post("/entity/shots", json={"project": SP, "code": "zzprobe_task_shot"})
    shot_id = made.add("shots", r.json()["data"]["id"])
    step_id = st["id"] if st else None

    for label, body in [
        ("{}", {}),
        ("content alone", {"content": "zzprobe_task_a"}),
        ("project alone", {"project": SP}),
        ("entity alone", {"entity": {"type": "Shot", "id": shot_id}}),
        ("project + content", {"project": SP, "content": "zzprobe_task_b"}),
        ("project + entity", {"project": SP, "entity": {"type": "Shot", "id": shot_id}}),
        ("project + content + entity + step",
         {"project": SP, "content": "zzprobe_task_c",
          "entity": {"type": "Shot", "id": shot_id}, "step": {"type": "Step", "id": step_id}}),
        ("content + entity, no project",
         {"content": "zzprobe_task_d", "entity": {"type": "Shot", "id": shot_id}}),
    ]:
        r = c.post(f"/entity/{SLUG}", json=body)
        rows.append(f"  POST {label:<36} -> {r.status_code}")
        if not r.ok:
            rows.append(f"    {flat(r)}")
            continue
        d = r.json()["data"]
        made.add(SLUG, d["id"])
        rows.append(f"    id={d['id']} content={d['attributes'].get('content')!r} "
                    f"cached_display_name={d['attributes'].get('cached_display_name')!r} "
                    f"entity={json.dumps((d['relationships'].get('entity') or {}).get('data'))} "
                    f"step={json.dumps((d['relationships'].get('step') or {}).get('data'))}")

    r = c.post(f"/entity/{SLUG}", json={"project": SP, "content": "zzprobe_task_sched",
                                        "entity": {"type": "Shot", "id": shot_id}})
    tid = made.add(SLUG, r.json()["data"]["id"])
    SCHED = "start_date,due_date,duration,est_in_mins,time_logs_sum,time_vs_est"
    rows.append("\n=== scheduling, write side")

    def put(label, body, fields=SCHED):
        r = c.put(f"/entity/{SLUG}/{tid}", json=body)
        if not r.ok:
            rows.append(f"  {label:<40} -> {r.status_code} {flat(r, 300)}")
            return
        a = c.get(f"/entity/{SLUG}/{tid}", params={"fields": fields}).json()["data"]["attributes"]
        rows.append(f"  {label:<40} -> 200 " + " ".join(f"{k}={a.get(k)!r}" for k in fields.split(",")))

    put("start_date + due_date", {"start_date": "2026-01-05", "due_date": "2026-01-09"})
    put("duration 480", {"duration": 480})
    put("duration 2400", {"duration": 2400})
    put("start_date only", {"start_date": "2026-02-02"})
    put("due_date only", {"due_date": "2026-02-13"})
    put("est_in_mins 600", {"est_in_mins": 600})
    put("time_logs_sum 60", {"time_logs_sum": 60})
    put("time_vs_est 60", {"time_vs_est": 60})
    put("time_percent_of_est 50", {"time_percent_of_est": 50})
    put("duration '2 days'", {"duration": "2 days"})

    rows.append("\n=== dependencies, write side")
    r = c.post(f"/entity/{SLUG}", json={"project": SP, "content": "zzprobe_task_up",
                                        "entity": {"type": "Shot", "id": shot_id},
                                        "start_date": "2026-01-05", "due_date": "2026-01-06"})
    up = made.add(SLUG, r.json()["data"]["id"])
    DEP = ("content,start_date,due_date,duration,upstream_tasks,downstream_tasks,"
           "sibling_tasks,dependency_violation,pinned")

    def show(i, label):
        d = c.get(f"/entity/{SLUG}/{i}", params={"fields": DEP}).json()["data"]
        rows.append(f"  {label:<34} {json.dumps(d['attributes'])}")
        rows.append(f"    {json.dumps(rel(d))[:400]}")

    r = c.put(f"/entity/{SLUG}/{tid}", json={"upstream_tasks": [{"type": "Task", "id": up}]})
    rows.append(f"  PUT upstream_tasks=[{up}] -> {r.status_code} " + ("" if r.ok else flat(r)))
    show(tid, "the dependent task")
    show(up, "the upstream task, reciprocal?")

    r = c.put(f"/entity/{SLUG}/{tid}", json={"start_date": "2026-01-01", "due_date": "2026-01-02"})
    rows.append(f"  PUT dependent dates before the upstream end -> {r.status_code}")
    show(tid, "after moving it earlier")

    r = c.put(f"/entity/{SLUG}/{up}", json={"downstream_tasks": []})
    rows.append(f"  PUT upstream downstream_tasks=[] -> {r.status_code} " + ("" if r.ok else flat(r, 300)))
    show(tid, "the dependent after the clear")

    for label, body in (("sibling_tasks", {"sibling_tasks": [{"type": "Task", "id": up}]}),
                        ("dependency_violation", {"dependency_violation": True})):
        r = c.put(f"/entity/{SLUG}/{tid}", json=body)
        rows.append(f"  PUT {label:<22} -> {r.status_code} " + ("" if r.ok else flat(r, 250)))

    rows.append("\n=== identity and link writes")

    def putback(label, body, fields):
        r = c.put(f"/entity/{SLUG}/{tid}", json=body)
        if not r.ok:
            rows.append(f"  {label:<42} -> {r.status_code} {flat(r, 300)}")
            return
        d = c.get(f"/entity/{SLUG}/{tid}", params={"fields": fields}).json()["data"]
        rows.append(f"  {label:<42} -> 200 {json.dumps(d['attributes'])} {json.dumps(rel(d))[:160]}")

    NAMES = "content,cached_display_name"
    putback("content='zzprobe_task_renamed'", {"content": "zzprobe_task_renamed"}, NAMES)
    putback("cached_display_name='zzprobe_cached'", {"cached_display_name": "zzprobe_cached"}, NAMES)
    putback(f"entity={{Task,{up}}}, valid_types omits Task", {"entity": {"type": "Task", "id": up}},
            "content,entity")
    putback("content=null, mandatory is true", {"content": None}, NAMES)
    putback("content=''", {"content": ""}, NAMES)

rows.append("\n=== sandbox left clean?")
for slug, f in ((SLUG, "content"), ("shots", "code")):
    d, _ = search(slug, [["project", "is", SP], [f, "starts_with", "zzprobe"]], (f,), size=200)
    rows.append(f"  {slug} in the sandbox matching zzprobe*: {len(d or [])}")
d, _ = search(SLUG, [["project", "is", SP], ["content", "starts_with", "New Task"]], ("content",))
rows.append(f"  tasks in the sandbox named 'New Task *': {len(d or [])}")

_lib.emit("entity_types/Task", "\n".join(rows), env)
