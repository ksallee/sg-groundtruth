"""Q: does adding a TaskDependency edge reschedule an unpinned downstream Task, or does only a date write?

Probe 087 measured the cascade from an upstream date write. A merge apply (recipe 015) adds edges
instead: the server copies a template's TaskDependency rows onto Tasks it claimed, between Tasks that
already hold dates. Two ways an edge appears, each with an unpinned and a pinned downstream Task:

  (a) POST /entity/task_dependencies between two dated Tasks where the downstream would violate.
  (b) The server's copy on claim: point each Task's `template_task` at a template task, then clear
      and set the Shot's `task_template` (recipe 015), the template holding edges the Tasks lack.

Preconditions: none from an operator. The probe provisions every row it reads (a Shot, 6 Tasks, one
template of 3 tasks and its 2 edges) and `_lib.Created` deletes them, failure included.

Writes only, in the sandbox, behind --write. Budget 60 s; wall time and call count are printed.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

T0 = time.monotonic()
env = _lib.load_env()
c = _lib.client()
CALLS = [0]
_request = c.request


def counted(method, path, **kw):
    CALLS[0] += 1
    return _request(method, path, **kw)


c.request = counted
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 092 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
DATES = {"start_date": "2026-03-02", "due_date": "2026-03-03"}   # Mon..Tue, every Task the same


def task_ref(i):
    return {"type": "Task", "id": i}


def show(label, ids):
    got = {t["id"]: t for t in T.search(c, "tasks", [["id", "in", list(ids.values())]],
                                         ["content", "start_date", "due_date", "duration", "pinned",
                                          "dependency_violation", "template_task", "upstream_tasks"])}
    rows.append(f"  {label}")
    for n, i in ids.items():
        a = got[i]["attributes"]
        up = [u["id"] for u in (T.rel(got[i], "upstream_tasks") or [])]
        up = [next((k for k, v in ids.items() if v == u), u) for u in up]
        tt = T.rel(got[i], "template_task")
        rows.append(f"    {n:<3} {a['start_date']}..{a['due_date']} dur={a['duration']!s:<4} "
                    f"pinned={a['pinned']!s:<5} violation={a['dependency_violation']!s:<5} "
                    f"upstream={up} template_task={'set' if tt else None}")


with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_092_shot"}))

    def task(name):
        return T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_092_{name}",
                                         **DATES})["id"]

    # (a) a direct TaskDependency create
    rows.append("=== (a) POST /entity/task_dependencies between dated Tasks")
    A = {n: task(n) for n in ("up", "dn", "pn")}
    r = c.put(f"/entity/tasks/{A['pn']}", json={"pinned": True})
    rows.append(f"  PUT pn pinned=true -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    show("before: three Tasks 03-02..03-03, no edges", A)
    for down in ("dn", "pn"):
        r = c.post("/entity/task_dependencies", json={"task": task_ref(A[down]), "dependent_task": task_ref(A["up"]),
                                                      "dependency_type": "finish-to-start-next-day"})
        rows.append(f"  POST task_dependencies {down} on up finish-to-start-next-day -> {r.status_code} "
                    f"{T.errs(r) if not r.ok else ''}")
        if r.ok:
            made.add("task_dependencies", r.json()["data"]["id"])
    show("after", A)

    # (b) the server's copy on claim, recipe 015
    rows.append("\n=== (b) claim, then clear and set task_template (recipe 015)")
    TT, tids = T.template(c, made, "zzprobe_092_tt",
                          {"zzprobe_092_a": {}, "zzprobe_092_b": {}, "zzprobe_092_c": {}},
                          [("zzprobe_092_b", "zzprobe_092_a", {"dependency_type": "finish-to-start-next-day"}),
                           ("zzprobe_092_c", "zzprobe_092_a", {"dependency_type": "finish-to-start-next-day"})])
    B = {n: task(n) for n in ("a", "b", "c")}
    r = c.put(f"/entity/tasks/{B['c']}", json={"pinned": True})
    rows.append(f"  template: a, b, c undated; edges b on a, c on a, finish-to-start-next-day")
    rows.append(f"  PUT c pinned=true -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    show("before: a, b, c on the Shot, 03-02..03-03, no edges", B)
    claim = [{"request_type": "update", "entity": "Task", "record_id": B[n],
              "data": {"template_task": task_ref(tids[f"zzprobe_092_{n}"])}} for n in ("a", "b", "c")]
    r = c.post("/entity/_batch", json={"requests": claim})
    rows.append(f"  _batch claim template_task on a, b, c -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    show("after the claim, before task_template", B)
    for v in (None, TT):
        r = c.put(f"/entity/shots/{sh['id']}", json={"task_template": v})
        rows.append(f"  PUT Shot task_template={v and 'tt'} -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    on = T.tasks_on(c, sh, ["content"])
    T.adopt(made, on)
    rows.append(f"  Tasks on the Shot: {len(on)} (6 made by the probe)")
    edges = T.deps_among(c, list(B.values()))
    for e in edges:
        made.add("task_dependencies", e["id"])
        a = e["attributes"]
        nm = {v: k for k, v in B.items()}
        rows.append(f"  TaskDependency {nm.get(T.rel(e, 'task')['id'])} on "
                    f"{nm.get(T.rel(e, 'dependent_task')['id'])} {a['dependency_type']} offset_days={a['offset_days']}")
    show("after", B)
    time.sleep(3)
    show("3 s later", B)

rows.append("\n=== left clean?")
dep_ids = [i for slug, i in made.rows if slug == "task_dependencies"]
task_ids = [i for slug, i in made.rows if slug == "tasks"]
rows.append(f"  Tasks zzprobe_092*, any project (template tasks carry none): "
            f"{len(T.search(c, 'tasks', [['content', 'starts_with', 'zzprobe_092']], ['content']))}")
rows.append(f"  live TaskDependency rows the probe made or adopted ({len(dep_ids)}): "
            f"{len(T.search(c, 'task_dependencies', [['id', 'in', dep_ids]], ['id']))}")
refs = [task_ref(i) for i in task_ids]
rows.append(f"  live TaskDependency rows touching any of its {len(task_ids)} Tasks: "
            f"{len({d['id'] for k in ('task', 'dependent_task') for d in T.search(c, 'task_dependencies', [[k, 'in', refs]], ['id'])})}")
rows.append(f"  TaskTemplates zzprobe_092*: "
            f"{len(T.search(c, 'task_templates', [['code', 'starts_with', 'zzprobe_092']], ['code']))}")
rows.append(f"  Shots zzprobe_092*: "
            f"{len(T.search(c, 'shots', [['project', 'is', P], ['code', 'starts_with', 'zzprobe_092']], ['code']))}")
rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")

_lib.emit("092_dependency_edge_reschedule", "\n".join(rows), env)
