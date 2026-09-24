"""Q: which `dependency_type` values does a TaskDependency take, and what do the type, `offset_days` and
`shift_ratio` do to the dependent Task's dates?

`entity_types/Task` found the join row and one type, `finish-to-start-next-day`, written by the
`upstream_tasks` shortcut. A sync app copying a template's dependencies has to write the row directly
with its type and offset. A bogus type first, since the 400 names the legal set (probe 017).

Writes only, in the sandbox, behind --write. Every row is deleted.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

env = _lib.load_env()
c = _lib.client()
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 085 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
DATES = "start_date,due_date,duration,pinned,dependency_violation"
# The upstream Task runs Monday to Friday; each dependent starts two weeks before it, two days long.
UP = {"start_date": "2026-03-02", "due_date": "2026-03-06"}
DOWN = {"start_date": "2026-02-16", "due_date": "2026-02-17"}


def dates(tid):
    a = c.get(f"/entity/tasks/{tid}", params={"fields": DATES}).json()["data"]["attributes"]
    return f"start={a['start_date']} due={a['due_date']} dur={a['duration']} pinned={a['pinned']} " \
           f"violation={a['dependency_violation']}"


with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_085_shot"}))
    n = [0]

    def task(extra):
        n[0] += 1
        return T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_085_{n[0]}",
                                         **extra})["id"]

    up = task(UP)
    rows.append(f"=== upstream {dates(up)}")

    rows.append("\n=== the vocabulary")
    for label, body in (("bogus", {"dependency_type": "zz_bogus"}), ("omitted", {}),
                        ("null", {"dependency_type": None}), ("upper case", {"dependency_type": "START-TO-START"})):
        d = task(DOWN)
        r = c.post("/entity/task_dependencies", json={"task": {"type": "Task", "id": d},
                                                      "dependent_task": {"type": "Task", "id": up}, **body})
        rows.append(f"  {label:<10} -> {r.status_code} "
                    + (T.errs(r) if not r.ok else f"stored {r.json()['data']['attributes'].get('dependency_type')!r}"))
        if r.ok:
            made.add("task_dependencies", r.json()["data"]["id"])

    rows.append("\n=== which side is which: POST {task: D, dependent_task: U}")
    d = task(DOWN)
    r = c.post("/entity/task_dependencies", json={"task": {"type": "Task", "id": d},
                                                  "dependent_task": {"type": "Task", "id": up},
                                                  "dependency_type": "finish-to-start-next-day"})
    dep = made.add("task_dependencies", r.json()["data"]["id"])
    row = c.get(f"/entity/task_dependencies/{dep}", params={"fields": "cached_display_name,task_id,dependent_task_id"})
    rows.append(f"  {r.status_code} {json.dumps(row.json()['data']['attributes'])}")
    dd = c.get(f"/entity/tasks/{d}", params={"fields": "upstream_tasks,downstream_tasks"}).json()["data"]
    rows.append(f"  D upstream_tasks {[x['id'] for x in T.rel(dd, 'upstream_tasks')]} (U={up}), "
                f"downstream {[x['id'] for x in T.rel(dd, 'downstream_tasks')]}")
    rows.append(f"  D after: {dates(d)}")

    rows.append(f"\n=== each type, offset_days, shift_ratio: a fresh D at {DOWN}")
    for typ in ("finish-to-start-next-day", "start-to-start", "finish-to-finish", "start-to-finish-next-day"):
        for extra in ({}, {"offset_days": 2}, {"offset_days": -1}, {"shift_ratio": 0.5}):
            d = task(DOWN)
            r = c.post("/entity/task_dependencies", json={"task": {"type": "Task", "id": d},
                                                          "dependent_task": {"type": "Task", "id": up},
                                                          "dependency_type": typ, **extra})
            if r.ok:
                made.add("task_dependencies", r.json()["data"]["id"])
            rows.append(f"  {typ:<25} {json.dumps(extra):<22} -> {r.status_code} "
                        + (dates(d) if r.ok else T.errs(r)))

    rows.append("\n=== change a live row")
    d = task(DOWN)
    r = c.post("/entity/task_dependencies", json={"task": {"type": "Task", "id": d},
                                                  "dependent_task": {"type": "Task", "id": up},
                                                  "dependency_type": "finish-to-start-next-day"})
    dep = made.add("task_dependencies", r.json()["data"]["id"])
    rows.append(f"  created FS:                     {dates(d)}")
    for body in ({"offset_days": 3}, {"dependency_type": "start-to-start"}, {"offset_days": None}):
        r = c.put(f"/entity/task_dependencies/{dep}", json=body)
        rows.append(f"  PUT {json.dumps(body):<28} -> {r.status_code} " + (dates(d) if r.ok else T.errs(r)))

    rows.append("\n=== the same pair twice, and a Task on itself")
    r = c.post("/entity/task_dependencies", json={"task": {"type": "Task", "id": d},
                                                  "dependent_task": {"type": "Task", "id": up},
                                                  "dependency_type": "finish-to-finish"})
    rows.append(f"  second row for the pair -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    if r.ok:
        made.add("task_dependencies", r.json()["data"]["id"])
    r = c.post("/entity/task_dependencies", json={"task": {"type": "Task", "id": up},
                                                  "dependent_task": {"type": "Task", "id": up}})
    rows.append(f"  task == dependent_task -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    if r.ok:
        made.add("task_dependencies", r.json()["data"]["id"])
    r = c.post("/entity/task_dependencies", json={"task": {"type": "Task", "id": up},
                                                  "dependent_task": {"type": "Task", "id": d}})
    rows.append(f"  the reverse edge, a cycle -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    if r.ok:
        made.add("task_dependencies", r.json()["data"]["id"])

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_085*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_085']], ['content']))}")

_lib.emit("085_task_dependency_types", "\n".join(rows), env)
