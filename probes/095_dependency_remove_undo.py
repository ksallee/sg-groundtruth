"""Q: how is one TaskDependency edge removed, what does that do to the downstream Task's dates, `pinned`
and `dependency_violation`, and can the edge be revived with its type and `offset_days`, or must it be
re-created, and what does re-creating do to the dates?

An editor with undo removes an edge and must put back exactly what was there. Probe 089 found that a
deleted Task revives with its dependency rows; this measures the edge on its own, by each route that
removes one: `DELETE` the row, and a `remove` on `upstream_tasks` or `downstream_tasks`.

Preconditions: none from an operator. The probe makes 1 Shot and 4 Tasks in the sandbox and deletes
them. Writes only, behind --write.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

if not _lib.writes_allowed():
    raise SystemExit("probe 095 writes; run with --write")
env = _lib.load_env()
c = _lib.client()

# Count calls without touching _lib (#76 owns that): wrap this client's request.
CALLS = [0]
_request = c.request


def counted(method, path, **kw):
    CALLS[0] += 1
    return _request(method, path, **kw)


c.request = counted
T0 = time.monotonic()

S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
rows = []
DEP_FIELDS = "task,dependent_task,dependency_type,offset_days"


def tref(i):
    return {"type": "Task", "id": i}


# Which fields on Task carry the edge. One schema call.
r = c.get("/schema/tasks/fields")
sch = r.json()["data"] if r.ok else {}
links = sorted(f"{k}:{v['data_type']['value']}:{v['editable']['value']}"
               for k, v in sch.items()
               if set((v.get("properties", {}).get("valid_types", {}) or {}).get("value") or [])
               & {"Task", "TaskDependency"})
rows.append(f"=== Task fields linking Task or TaskDependency (name:type:editable): {links}")

with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_095_shot"}))

    def task(name, start, due):
        return T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_095_{name}",
                                         "start_date": start, "due_date": due})["id"]

    ids = {"up": task("up", "2026-03-02", "2026-03-06")}
    for n in ("d", "g", "e", "f"):
        ids[n] = task(n, "2026-02-16", "2026-02-17")
    U = tref(ids["up"])

    def edge(down, typ, off):
        return T.post(c, made, "task_dependencies", {"task": tref(ids[down]), "dependent_task": U,
                                                     "dependency_type": typ, "offset_days": off})["id"]

    dep = {"d": edge("d", "finish-to-finish", 1), "g": edge("g", "finish-to-start-next-day", 2),
           "e": edge("e", "start-to-start", 1),
           "f": edge("f", "finish-to-start-next-day", 2)}

    def state(label, names=("d", "g", "e", "f")):
        rows.append(f"  {label}")
        r = T.search(c, "tasks", [["id", "in", [ids[n] for n in ("up",) + tuple(names)]]],
                     ["start_date", "due_date", "pinned", "dependency_violation", "upstream_tasks",
                      "downstream_tasks"])
        by = {t["id"]: t for t in r}
        for n in ("up",) + tuple(names):
            t = by[ids[n]]
            a = t["attributes"]
            rows.append(f"    {n:<2} {a['start_date']}..{a['due_date']} pinned={a['pinned']} "
                        f"violation={a['dependency_violation']} "
                        f"up={[x['id'] for x in T.rel(t, 'upstream_tasks')]} "
                        f"down={[x['id'] for x in T.rel(t, 'downstream_tasks')]}")

    def rows_between(label):
        """Every TaskDependency row between up and d/e/f, live and retired."""
        out = {}
        for mode in ("active", "retired"):
            r = c.post("/entity/task_dependencies/_search", headers=T.ARR,
                       json={"filters": [["dependent_task", "is", U]], "fields": DEP_FIELDS.split(","),
                             "options": {"return_only": mode}})
            out[mode] = ([(x["id"], x["attributes"]["dependency_type"], x["attributes"]["offset_days"])
                          for x in r.json()["data"]] if r.ok else T.errs(r))
        rows.append(f"    rows {label}: live={out['active']}")
        rows.append(f"    {' ' * len(label)}   retired={out['retired']}")

    rows.append(f"\n=== up={ids['up']} 03-02..03-06; d, g, e, f written 02-16..02-17")
    rows.append(f"    d on up finish-to-finish +1 row {dep['d']}; g finish-to-start-next-day +2 row {dep['g']}; "
                f"e start-to-start +1 row {dep['e']}; f finish-to-start-next-day +2 row {dep['f']}")
    r = c.put(f"/entity/tasks/{ids['d']}", json={"start_date": "2026-02-23", "due_date": "2026-02-24"})
    rows.append(f"  PUT d 02-23..02-24 (pins it, before up ends) -> {r.status_code}")
    state("linked")
    rows_between("linked")

    rows.append("\n=== remove")
    for n in "dg":
        r = c.delete(f"/entity/task_dependencies/{dep[n]}")
        rows.append(f"  DELETE /entity/task_dependencies/{dep[n]} ({n}) -> {r.status_code} {r.text[:200]!r}")
    r = c.put(f"/entity/tasks/{ids['e']}",
              json={"upstream_tasks": {"multi_entity_update_mode": "remove", "value": [U]}})
    rows.append(f"  PUT e upstream_tasks remove [up] -> {r.status_code} {'' if r.ok else T.errs(r)}")
    r = c.put(f"/entity/tasks/{ids['up']}",
              json={"downstream_tasks": {"multi_entity_update_mode": "remove", "value": [tref(ids['f'])]}})
    rows.append(f"  PUT up downstream_tasks remove [f] -> {r.status_code} {'' if r.ok else T.errs(r)}")
    for n in "dgef":
        r = c.get(f"/entity/task_dependencies/{dep[n]}", params={"fields": DEP_FIELDS})
        rows.append(f"    GET row {dep[n]} ({n}) -> {r.status_code}")
    state("after remove")
    rows_between("after remove")
    r = c.put(f"/entity/tasks/{ids['up']}", json={"due_date": "2026-03-13"})
    rows.append(f"  PUT up due 03-13 -> {r.status_code}")
    state("after up moves")

    rows.append("\n=== revive the retired rows")
    for n in "dgef":
        r = c.post(f"/entity/task_dependencies/{dep[n]}", params={"revive": 1})
        rows.append(f"  POST /entity/task_dependencies/{dep[n]}?revive=1 ({n}) -> {r.status_code} "
                    f"{json.dumps(r.json().get('meta')) if r.ok else T.errs(r)}")
    state("after revive")
    rows_between("after revive")

    rows.append("\n=== re-create instead: remove d's, g's and e's edges again, then write them back")
    for n in "dg":
        r = c.delete(f"/entity/task_dependencies/{dep[n]}")
        rows.append(f"  DELETE row {dep[n]} ({n}) -> {r.status_code}")
    r = c.put(f"/entity/tasks/{ids['up']}", json={"due_date": "2026-03-20"})
    rows.append(f"  PUT up due 03-20 while unlinked -> {r.status_code}")
    state("removed again", ("d", "g", "e"))
    new = {}
    for n, typ, off in (("d", "finish-to-finish", 1), ("g", "finish-to-start-next-day", 2)):
        r = c.post("/entity/task_dependencies", json={"task": tref(ids[n]), "dependent_task": U,
                                                      "dependency_type": typ, "offset_days": off})
        new[n] = made.add("task_dependencies", r.json()["data"]["id"]) if r.ok else None
        rows.append(f"  POST row {n} {typ} {off:+d} -> {r.status_code} id={new[n]} {'' if r.ok else T.errs(r)}")
    r = c.put(f"/entity/tasks/{ids['e']}",
              json={"upstream_tasks": {"multi_entity_update_mode": "add", "value": [U]}})
    rows.append(f"  PUT e upstream_tasks add [up] -> {r.status_code} {'' if r.ok else T.errs(r)}")
    state("re-created", ("d", "g", "e"))
    rows_between("re-created")
    r = c.post(f"/entity/task_dependencies/{dep['g']}", params={"revive": 1})
    rows.append(f"  revive g's old row {dep['g']} beside its new one -> {r.status_code} "
                f"{json.dumps(r.json().get('meta')) if r.ok else T.errs(r)}")
    rows_between("after second revive")
    live = T.search(c, "task_dependencies", [["dependent_task", "is", U]], ["task"])
    for x in live:
        if ("task_dependencies", x["id"]) not in made.rows:
            made.add("task_dependencies", x["id"])

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_095*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_095']], ['content']))}"
            f"  Shots: {len(T.search(c, 'shots', [['project', 'is', P], ['code', 'starts_with', 'zzprobe_095']], ['code']))}")
rows.append(f"\n=== run: {time.monotonic() - T0:.1f}s wall, {CALLS[0]} calls")

_lib.emit("095_dependency_remove_undo", "\n".join(rows), env)
