"""Q: how is a TaskTemplate addressed and created, and where are the Tasks it holds?

A task template sync app reads a template's tasks and compares them with the Tasks an entity already
has. Nothing in the corpus says where those template tasks are stored, what they carry (step, dates,
assignees, order, dependencies) or how a generated Task points back at them.

Read-only against the whole site: templates are site-wide. The create contract runs behind --write,
and every row it makes is deleted.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []


def errs(r):
    """The whole errors[] object, `source` included (probe 017)."""
    try:
        return json.dumps(r.json().get("errors"), indent=None)
    except ValueError:
        return r.text


def search(slug, filters, fields, size=500):
    out, page = [], 1
    while True:
        r = c.post(f"/entity/{slug}/_search", headers=ARR,
                   json={"filters": filters, "fields": fields, "page": {"size": size, "number": page}})
        if not r.ok:
            raise SystemExit(f"{slug} _search {r.status_code} {errs(r)}")
        d = r.json()["data"]
        out += d
        if len(d) < size:
            return out
        page += 1


def rel(d, k):
    return ((d.get("relationships") or {}).get(k) or {}).get("data")


def top(d, k):
    return (d.get(k) or {}).get("value")


# ---------------------------------------------------------------- path and scope
rows.append("=== path and scope")
for path in ("/entity/task_templates", "/entity/TaskTemplate", "/entity/tasktemplates"):
    r = c.get(path, params={"fields": "code", "page[size]": 1})
    rows.append(f"  GET {path:<24} -> {r.status_code} "
                + (r.json()["data"][0]["links"]["self"] if r.ok and r.json()["data"] else errs(r)))
sch = c.get("/schema/TaskTemplate/fields").json()["data"]
rows.append(f"  {len(sch)} fields; 'project' in fields: {'project' in sch}")
rows.append(f"  {'field':<22}{'data_type':<14}{'editable':<10}{'mandatory':<11}{'unique':<8}valid_types")
for n, d in sorted(sch.items()):
    rows.append(f"  {n:<22}{top(d, 'data_type'):<14}{str(top(d, 'editable')):<10}"
                f"{str(top(d, 'mandatory')):<11}{str(top(d, 'unique')):<8}"
                f"{(d.get('properties', {}).get('valid_types') or {}).get('value')}")
r = c.post("/entity/task_templates/_search", headers=ARR,
           json={"filters": [["project", "is", {"type": "Project", "id": 1}]], "fields": ["code"]})
rows.append(f"  filter on project -> {r.status_code} {errs(r) if not r.ok else ''}")

# ---------------------------------------------------------------- the rows
rows.append("\n=== templates on the site")
tts = search("task_templates", [], ["code", "entity_type", "task_count", "projects", "description"])
_lib.note_from(tts)
rows.append(f"  {len(tts)} templates; by entity_type {dict(Counter(t['attributes']['entity_type'] for t in tts))}")
rows.append(f"  task_count python types {Counter(type(t['attributes']['task_count']).__name__ for t in tts)}")
rows.append(f"  with projects set: {sum(1 for t in tts if rel(t, 'projects'))}")
rows.append(f"  one row: {json.dumps(tts[0]['attributes'])}")

# ---------------------------------------------------------------- template tasks
rows.append("\n=== where the template's own Tasks are: Task.task_template")
TF = ["content", "entity", "project", "step", "task_template", "template_task", "start_date", "due_date",
      "duration", "est_in_mins", "task_assignees", "task_reviewers", "sg_sort_order", "milestone",
      "sg_status_list", "upstream_tasks", "downstream_tasks", "pinned", "sg_description"]
held = search("tasks", [["task_template", "is_not", None]], TF)
by_proj = Counter("project null" if rel(t, "project") is None else "project set" for t in held)
rows.append(f"  Tasks with task_template set: {len(held)}, {dict(by_proj)}")
tpl = [t for t in held if rel(t, "project") is None]
gen = [t for t in held if rel(t, "project") is not None]
rows.append(f"  of the project-null ones, entity null: {sum(1 for t in tpl if rel(t, 'entity') is None)}"
            f", template_task set: {sum(1 for t in tpl if rel(t, 'template_task'))}")
rows.append(f"  of the project-set ones, template_task set: {sum(1 for t in gen if rel(t, 'template_task'))}"
            f", entity set: {sum(1 for t in gen if rel(t, 'entity'))}")
per_tt = Counter(rel(t, "task_template")["id"] for t in tpl)
mismatch = [(t["id"], t["attributes"]["task_count"], per_tt.get(t["id"], 0)) for t in tts
            if int(t["attributes"]["task_count"] or 0) != per_tt.get(t["id"], 0)]
rows.append(f"  task_count equals the project-null Task count on {len(tts) - len(mismatch)} of {len(tts)}"
            f"; mismatches (id, task_count, counted) {mismatch[:5]}")

rows.append("\n  fill across the template tasks:")


def filled(t, k):
    a = t["attributes"]
    if k in a:
        return a[k] not in (None, "", False, [])
    v = rel(t, k)
    return v not in (None, [])


for k in TF[3:]:
    rows.append(f"    {k:<18} {sum(1 for t in tpl if filled(t, k)):>4} of {len(tpl)}")
rows.append(f"  sg_status_list values {dict(Counter(t['attributes']['sg_status_list'] for t in tpl))}")
rows.append(f"  duration values {dict(Counter(t['attributes']['duration'] for t in tpl).most_common(5))}")
ex = next((t for t in tpl if rel(t, "upstream_tasks")), tpl[0])
_lib.note_from(ex)
rows.append(f"  one template task: {json.dumps(ex['attributes'])}")
rows.append(f"    upstream_tasks {json.dumps(rel(ex, 'upstream_tasks'))}")
rows.append(f"    step {json.dumps(rel(ex, 'step'))} task_template {json.dumps(rel(ex, 'task_template'))}")

rows.append("\n=== a generated Task, pointing back")
if gen:
    g = next((t for t in gen if rel(t, "template_task")), gen[0])
    _lib.note_from(g)
    rows.append(f"  template_task {json.dumps(rel(g, 'template_task'))}")
    rows.append(f"  task_template {json.dumps(rel(g, 'task_template'))}  entity type "
                f"{(rel(g, 'entity') or {}).get('type')}")
    gt = rel(g, "template_task")
    if gt:
        src = next((t for t in tpl if t["id"] == gt["id"]), None)
        rows.append(f"  template_task is a project-null template task: {src is not None}")
gen_tt = search("tasks", [["template_task", "is_not", None]], ["task_template", "project"])
rows.append(f"  Tasks with template_task set: {len(gen_tt)}; of those task_template also set: "
            f"{sum(1 for t in gen_tt if rel(t, 'task_template'))}")

rows.append("\n=== TaskDependency rows between template tasks")
ids = [t["id"] for t in tpl]
deps = []
for i in range(0, len(ids), 200):
    deps += search("task_dependencies", [["task", "in", [{"type": "Task", "id": x} for x in ids[i:i + 200]]]],
                   ["dependency_type", "offset_days", "shift_ratio", "task", "dependent_task"])
up_links = sum(len(rel(t, "upstream_tasks") or []) for t in tpl)
rows.append(f"  {len(deps)} rows with a template task as `task`; upstream_tasks links on template tasks: {up_links}")
rows.append(f"  dependency_type {dict(Counter(d['attributes']['dependency_type'] for d in deps))}")
rows.append(f"  offset_days {dict(Counter(d['attributes']['offset_days'] for d in deps))}")
rows.append(f"  shift_ratio {dict(Counter(d['attributes']['shift_ratio'] for d in deps))}")

if not _lib.writes_allowed():
    rows.append("\n(no --write: create contract skipped)")
    _lib.emit("entity_types/TaskTemplate", "\n".join(rows), env)
    raise SystemExit

# ---------------------------------------------------------------- writes
S = _lib.sandbox_id(c, env)
rows.append("\n=== create contract")
with _lib.Created(c) as made:
    for label, body in [
        ("{}", {}),
        ("code alone", {"code": "zzprobe_tt_a"}),
        ("entity_type alone", {"entity_type": "Shot"}),
        ("code + entity_type Shot", {"code": "zzprobe_tt_b", "entity_type": "Shot"}),
        ("code + entity_type 'Nope'", {"code": "zzprobe_tt_c", "entity_type": "Nope"}),
        ("code + entity_type Task", {"code": "zzprobe_tt_d", "entity_type": "Task"}),
        ("code + entity_type 'shots'", {"code": "zzprobe_tt_e", "entity_type": "shots"}),
    ]:
        r = c.post("/entity/task_templates", json=body)
        rows.append(f"  POST {label:<28} -> {r.status_code} "
                    + (json.dumps(r.json()["data"]["attributes"]) if r.ok else errs(r)))
        if r.ok:
            made.add("task_templates", r.json()["data"]["id"])
    r = c.post("/entity/task_templates", json={"code": "zzprobe_tt_b", "entity_type": "Shot"})
    rows.append(f"  POST the same code again -> {r.status_code}")
    if r.ok:
        made.add("task_templates", r.json()["data"]["id"])

    tt = next(i for s_, i in made.rows if s_ == "task_templates")
    r = c.put(f"/entity/task_templates/{tt}", json={"entity_type": "Asset"})
    rows.append(f"  PUT entity_type Asset (schema: editable False) -> {r.status_code} {errs(r) if not r.ok else ''}"
                f"; reads back {c.get(f'/entity/task_templates/{tt}', params={'fields': 'entity_type'}).json()['data']['attributes']['entity_type']!r}")
    r = c.put(f"/entity/task_templates/{tt}", json={"task_count": 9})
    rows.append(f"  PUT task_count 9 -> {r.status_code} {errs(r) if not r.ok else ''}")

    rows.append("\n  a template task: Task with task_template, no project")
    TT = {"type": "TaskTemplate", "id": tt}
    for label, body in [
        ("content + task_template", {"content": "zzprobe_tt_task", "task_template": TT}),
        ("+ project (sandbox)", {"content": "zzprobe_tt_task_p", "task_template": TT,
                                 "project": {"type": "Project", "id": S}}),
    ]:
        r = c.post("/entity/tasks", json=body)
        rows.append(f"  POST {label:<28} -> {r.status_code} {errs(r) if not r.ok else ''}")
        if r.ok:
            d = r.json()["data"]
            made.add("tasks", d["id"])
            rows.append(f"    project {json.dumps(rel(d, 'project'))} sg_status_list "
                        f"{d['attributes'].get('sg_status_list')!r}")
    r = c.get(f"/entity/task_templates/{tt}", params={"fields": "task_count"})
    rows.append(f"  task_count after: {r.json()['data']['attributes']['task_count']!r}")

    rows.append("\n  delete a template that still holds a task")
    r = c.post("/entity/task_templates", json={"code": "zzprobe_tt_doomed", "entity_type": "Shot"})
    doomed = r.json()["data"]["id"]
    r = c.post("/entity/tasks", json={"content": "zzprobe_tt_orphan",
                                      "task_template": {"type": "TaskTemplate", "id": doomed}})
    orphan = made.add("tasks", r.json()["data"]["id"])
    r = c.delete(f"/entity/task_templates/{doomed}")
    rows.append(f"  DELETE the template -> {r.status_code}")
    r = c.get(f"/entity/tasks/{orphan}", params={"fields": "content,task_template"})
    rows.append(f"  GET its task -> {r.status_code} "
                + (json.dumps(rel(r.json()["data"], "task_template")) if r.ok else errs(r)))

rows.append("\n=== left clean?")
left = search("task_templates", [["code", "starts_with", "zzprobe"]], ["code"])
rows.append(f"  templates matching zzprobe*: {len(left)}")

_lib.emit("entity_types/TaskTemplate", "\n".join(rows), env)
