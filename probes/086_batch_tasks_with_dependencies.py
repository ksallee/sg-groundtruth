"""Q: can one `_batch` create Tasks and link them to each other, and if not, what is the fewest calls?

Recipe 002 found a batch cannot reference an id it creates. A sync app copying a template creates N
Tasks and their dependencies; this measures the placeholder once more on `upstream_tasks`, then the
two-call route (Tasks, then TaskDependency rows or `upstream_tasks` updates), what each does to the
dates, and whether a bad dependency rolls the rest of its batch back.

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
    raise SystemExit("probe 086 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}


def batch(reqs):
    t0 = time.time()
    r = c.post("/entity/_batch", json={"requests": reqs})
    return r, time.time() - t0


def dates(ids):
    out = []
    for i in ids:
        d = c.get(f"/entity/tasks/{i}", params={"fields": "content,start_date,due_date,upstream_tasks"}).json()["data"]
        a = d["attributes"]
        out.append(f"{a['content'][-2:]}: {a['start_date']}..{a['due_date']} "
                   f"up={[x['id'] for x in T.rel(d, 'upstream_tasks')]}")
    return "  ".join(out)


def create(sh, name, extra=None):
    return {"request_type": "create", "entity": "Task",
            "data": {"project": P, "entity": sh, "content": name,
                     "start_date": "2026-03-02", "due_date": "2026-03-03", **(extra or {})}}


with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_086_shot"}))

    rows.append("=== one batch: create A, create B with upstream_tasks pointing at request 0")
    for label, up in (("{type: Task, id: '$0'}", {"type": "Task", "id": "$0"}),
                      ("{type: Task, id: -1}", {"type": "Task", "id": -1})):
        r, dt = batch([create(sh, "zzprobe_086_x1"), create(sh, "zzprobe_086_x2", {"upstream_tasks": [up]})])
        rows.append(f"  {label:<26} -> {r.status_code} {T.errs(r) if not r.ok else ''}")
        if r.ok:
            for row in r.json()["data"]:
                made.add("tasks", row["data"]["id"])
    left = T.search(c, "tasks", [["entity", "is", sh]], ["content"])
    rows.append(f"  Tasks on the Shot after the refusals: {len(left)}")

    rows.append("\n=== two calls, route 1: create the Tasks, then TaskDependency rows")
    r, dt = batch([create(sh, f"zzprobe_086_a{i}") for i in range(1, 5)])
    ids = [made.add("tasks", row["data"]["id"]) for row in r.json()["data"]]
    rows.append(f"  batch 1: 4 creates -> {r.status_code} in {dt:.1f}s")
    reqs = [{"request_type": "create", "entity": "TaskDependency",
             "data": {"task": {"type": "Task", "id": ids[1]}, "dependent_task": {"type": "Task", "id": ids[0]},
                      "dependency_type": "start-to-start", "offset_days": 1}},
            {"request_type": "create", "entity": "TaskDependency",
             "data": {"task": {"type": "Task", "id": ids[2]}, "dependent_task": {"type": "Task", "id": ids[1]}}},
            {"request_type": "create", "entity": "TaskDependency",
             "data": {"task": {"type": "Task", "id": ids[3]}, "dependent_task": {"type": "Task", "id": ids[2]},
                      "dependency_type": "finish-to-finish"}}]
    r, dt = batch(reqs)
    rows.append(f"  batch 2: 3 TaskDependency creates -> {r.status_code} in {dt:.1f}s "
                f"{T.errs(r) if not r.ok else ''}")
    if r.ok:
        for row in r.json()["data"]:
            made.add("task_dependencies", row["data"]["id"])
        rows.append(f"  row 0: {json.dumps(r.json()['data'][0]['data']['attributes'])}")
    rows.append(f"  dates: {dates(ids)}")
    rows.append(f"  rows read back: {[(d['attributes']['dependency_type'], d['attributes']['offset_days']) for d in T.deps_among(c, ids)]}")

    rows.append("\n=== two calls, route 2: create the Tasks, then update upstream_tasks")
    r, dt = batch([create(sh, f"zzprobe_086_b{i}") for i in range(1, 4)])
    ids2 = [made.add("tasks", row["data"]["id"]) for row in r.json()["data"]]
    r, dt = batch([{"request_type": "update", "entity": "Task", "record_id": ids2[1],
                    "data": {"upstream_tasks": [{"type": "Task", "id": ids2[0]}]}},
                   {"request_type": "update", "entity": "Task", "record_id": ids2[2],
                    "data": {"upstream_tasks": [{"type": "Task", "id": ids2[1]}]}}])
    rows.append(f"  batch 2: 2 updates -> {r.status_code} in {dt:.1f}s {T.errs(r) if not r.ok else ''}")
    rows.append(f"  dates: {dates(ids2)}")
    rows.append(f"  rows read back: {[d['attributes']['dependency_type'] for d in T.deps_among(c, ids2)]}")
    for d in T.deps_among(c, ids2):
        made.add("task_dependencies", d["id"])

    rows.append("\n=== route 3: create level 2 with upstream_tasks set to level-1 ids")
    r, dt = batch([create(sh, "zzprobe_086_c1")])
    c1 = made.add("tasks", r.json()["data"][0]["data"]["id"])
    r, dt = batch([create(sh, "zzprobe_086_c2", {"upstream_tasks": [{"type": "Task", "id": c1}]}),
                   create(sh, "zzprobe_086_c3", {"upstream_tasks": [{"type": "Task", "id": c1}]})])
    rows.append(f"  2 creates with upstream_tasks -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    ids3 = [c1] + ([made.add("tasks", row["data"]["id"]) for row in r.json()["data"]] if r.ok else [])
    rows.append(f"  dates: {dates(ids3)}")
    d3 = T.deps_among(c, ids3)
    rows.append(f"  rows read back: {[d['attributes']['dependency_type'] for d in d3]}")
    for d in d3:
        made.add("task_dependencies", d["id"])
    v = T.search(c, "tasks", [["id", "in", ids3]], ["dependency_violation", "pinned"])
    rows.append(f"  dependency_violation {[x['attributes']['dependency_violation'] for x in v]} "
                f"pinned {[x['attributes']['pinned'] for x in v]}")
    single = T.post(c, made, "tasks", {**create(sh, "zzprobe_086_c4")["data"],
                                       "upstream_tasks": [{"type": "Task", "id": c1}]})
    rows.append(f"  the same create as a plain POST /entity/tasks: {dates([single['id']])}")
    for d in T.deps_among(c, [single["id"]]):
        made.add("task_dependencies", d["id"])
    r = c.put(f"/entity/tasks/{ids3[1]}", json={"sg_description": "touch"})
    rows.append(f"  PUT an unrelated field on c2 -> {r.status_code}; dates: {dates(ids3)}")

    rows.append("\n=== rollback: a good dependency and a loop in one batch")
    before = len(T.deps_among(c, ids))
    r, dt = batch([{"request_type": "create", "entity": "TaskDependency",
                    "data": {"task": {"type": "Task", "id": ids[3]}, "dependent_task": {"type": "Task", "id": ids[0]}}},
                   {"request_type": "create", "entity": "TaskDependency",
                    "data": {"task": {"type": "Task", "id": ids[0]}, "dependent_task": {"type": "Task", "id": ids[3]}}}])
    rows.append(f"  -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    if r.ok:
        for row in r.json()["data"]:
            made.add("task_dependencies", row["data"]["id"])
    rows.append(f"  TaskDependency rows among route-1 Tasks: {before} before, {len(T.deps_among(c, ids))} after")

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_086*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_086']], ['content']))}")

_lib.emit("086_batch_tasks_with_dependencies", "\n".join(rows), env)
