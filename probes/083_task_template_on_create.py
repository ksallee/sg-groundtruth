"""Q: does creating a Shot with `task_template` generate Tasks, and what do they copy from the template?

`entity_types/Shot` claimed the template is applied on create without a measurement. This builds a
sandbox template of three tasks, one dependency with a type and an offset, an assignee, a status, an
order, a duration and dates, creates Shots with it by each create path, and reads what came out.

Writes only, in the sandbox, behind --write. Every row is deleted.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

env = _lib.load_env()
c = _lib.client()
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 083 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
GROUP = T.empty_group(c)
step_a, step_b, step_c = (ST[k] for k in sorted(ST)[:3])

TASKS = {
    "zzprobe_083_a": {"step": {"type": "Step", "id": step_a}, "sg_sort_order": 10, "duration": 960,
                      "est_in_mins": 600, "sg_status_list": "na", "sg_description": "from template",
                      "task_assignees": [GROUP] if GROUP else []},
    "zzprobe_083_b": {"step": {"type": "Step", "id": step_b}, "sg_sort_order": 20, "duration": 480,
                      "milestone": True},
    "zzprobe_083_c": {"step": {"type": "Step", "id": step_c}, "sg_sort_order": 30,
                      "start_date": "2026-03-02", "due_date": "2026-03-04"},
}
DEPS = [("zzprobe_083_b", "zzprobe_083_a", {"dependency_type": "start-to-start", "offset_days": 2}),
        ("zzprobe_083_c", "zzprobe_083_b", {})]

with _lib.Created(c) as made:
    TT, tids = T.template(c, made, "zzprobe_083_tt", TASKS, DEPS)
    rows.append("=== the template, read back")
    for t in T.search(c, "tasks", [["task_template", "is", TT]], T.TASK_FIELDS):
        rows.append("  " + T.line(t) + f" assignees={len(T.rel(t, 'task_assignees') or [])}")
    for d in T.deps_among(c, list(tids.values())):
        a = d["attributes"]
        rows.append(f"  dep task={T.rel(d, 'task')['name']} dependent_task={T.rel(d, 'dependent_task')['name']} "
                    f"type={a['dependency_type']} offset_days={a['offset_days']}")

    # ------------------------------------------------------------ POST /entity/shots
    rows.append("\n=== POST /entity/shots with task_template")
    t0 = time.time()
    shot = T.post(c, made, "shots", {"project": P, "code": "zzprobe_083_shot", "task_template": TT})
    rows.append(f"  201 in {time.time() - t0:.1f}s; response task_template "
                f"{json.dumps(T.rel(shot, 'task_template'))}, tasks {json.dumps(T.rel(shot, 'tasks'))}")
    SH = T.ref(shot)
    got = T.tasks_on(c, SH)
    T.adopt(made, got)
    rows.append(f"  Tasks on the Shot immediately after: {len(got)}")
    for t in got:
        rows.append("    " + T.line(t))
    if got:
        g = next(t for t in got if t["attributes"]["content"] == "zzprobe_083_a")
        a = g["attributes"]
        rows.append(f"  a in full: est_in_mins={a['est_in_mins']} milestone={a['milestone']} "
                    f"description={a['sg_description']!r} pinned={a['pinned']}")
        rows.append(f"    project={json.dumps(T.rel(g, 'project'))}")
        rows.append(f"    task_template={json.dumps(T.rel(g, 'task_template'))} "
                    f"template_task={json.dumps(T.rel(g, 'template_task'))}")
        rows.append(f"    task_assignees={json.dumps(T.rel(g, 'task_assignees'))}")
        b = next(t for t in got if t["attributes"]["content"] == "zzprobe_083_b")
        rows.append(f"  b milestone={b['attributes']['milestone']} upstream={json.dumps(T.rel(b, 'upstream_tasks'))}")
        rows.append(f"  created_at of the Tasks {sorted({t['attributes']['created_at'] for t in got})}, "
                    f"shot {shot['attributes']['created_at']}")
        for d in T.deps_among(c, [t["id"] for t in got]):
            a = d["attributes"]
            rows.append(f"  generated dep task={T.rel(d, 'task')['name']} "
                        f"dependent_task={T.rel(d, 'dependent_task')['name']} "
                        f"type={a['dependency_type']} offset_days={a['offset_days']} shift_ratio={a['shift_ratio']}")
    r = c.get(f"/entity/shots/{shot['id']}", params={"fields": "task_template,tasks"})
    d = r.json()["data"]
    rows.append(f"  GET the Shot: task_template {json.dumps(T.rel(d, 'task_template'))} "
                f"tasks {len(T.rel(d, 'tasks') or [])}")
    later = T.tasks_on(c, SH, settle=5)
    rows.append(f"  Tasks on the Shot 5s later: {len(later)}")

    # ------------------------------------------------------------ POST /entity/_batch
    rows.append("\n=== the same create inside POST /entity/_batch")
    r = c.post("/entity/_batch", json={"requests": [{"request_type": "create", "entity": "Shot",
                                                     "data": {"project": P, "code": "zzprobe_083_batch",
                                                              "task_template": TT}}]})
    rows.append(f"  {r.status_code} {T.errs(r) if not r.ok else ''}")
    if r.ok:
        bid = r.json()["data"][0]["data"]["id"]
        made.add("shots", bid)
        got = T.tasks_on(c, {"type": "Shot", "id": bid})
        T.adopt(made, got)
        rows.append(f"  Tasks on the batch-created Shot: {len(got)} "
                    f"{sorted(t['attributes']['content'] for t in got)}")

    # ------------------------------------------------------------ entity_type mismatch
    rows.append("\n=== a template whose entity_type is Asset, on a Shot create")
    TA, _ = T.template(c, made, "zzprobe_083_tt_asset", {"zzprobe_083_asset_task": {}}, entity_type="Asset")
    r = c.post("/entity/shots", json={"project": P, "code": "zzprobe_083_mismatch", "task_template": TA})
    rows.append(f"  POST -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    if r.ok:
        mid = made.add("shots", r.json()["data"]["id"])
        got = T.tasks_on(c, {"type": "Shot", "id": mid})
        T.adopt(made, got)
        rows.append(f"  Tasks generated: {len(got)} {sorted(t['attributes']['content'] for t in got)}")

    # ------------------------------------------------------------ a Task field on the create body
    rows.append("\n=== create a Shot with task_template: null, then the Task list")
    r = c.post("/entity/shots", json={"project": P, "code": "zzprobe_083_null", "task_template": None})
    nid = made.add("shots", r.json()["data"]["id"])
    rows.append(f"  POST -> {r.status_code}; Tasks: {len(T.tasks_on(c, {'type': 'Shot', 'id': nid}))}")

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_083*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_083']], ['content']))}")
rows.append(f"  templates zzprobe_083*: "
            f"{len(T.search(c, 'task_templates', [['code', 'starts_with', 'zzprobe_083']], ['code']))}")

_lib.emit("083_task_template_on_create", "\n".join(rows), env)
