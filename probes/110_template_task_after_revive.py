"""Q: a Task generated from template A (so `template_task` points at A.x) is deleted, then revived.
Is `template_task` restored? And while the Task is retired, does writing the Shot's `task_template`
to A make a new Task for A.x; after the revive, do two Tasks then point at A.x? Measured both orders
(template write then revive; revive then template write) and both delete routes (`DELETE` and a
`delete` inside `_batch`), one Shot per combination.

The template write is `task_template` null then A (probe 084: the apply runs only when the value
changes). An undo writes B -> A (probes 096, 104); that transition is not measured here.

Controls: A.y's Task is live through every step and must never be duplicated (negative); the
template-first order with the Task retired is where a new Task can appear (positive).

Preconditions: none from an operator. The probe provisions one 2-task template with one edge and
4 Shots made with it; `_lib.Created` deletes them, failure included.

Writes only, in the sandbox, behind --write. Budget 60 s; wall time and call count are printed.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

if not _lib.writes_allowed():
    raise SystemExit("probe 110 writes; run with --write")
T0 = time.monotonic()
env = _lib.load_env()
c = _lib.client()

# Count calls without touching _lib (#76 owns that). Created's deletes go through c.request too.
CALLS = [0]
_request = c.request


def counted(method, path, **kw):
    CALLS[0] += 1
    return _request(method, path, **kw)


c.request = counted
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
step_x, step_y = (ST[k] for k in sorted(ST)[:2])
rows = []
seen = set()


def tref(i):
    return {"type": "Task", "id": i}


with _lib.Created(c) as made:
    TT, tid = T.template(c, made, "zzprobe_110_tt",
                         {"zzprobe_110_x": {"step": {"type": "Step", "id": step_x}, "sg_description": "tpl x"},
                          "zzprobe_110_y": {"step": {"type": "Step", "id": step_y}, "sg_description": "tpl y"}},
                         [("zzprobe_110_y", "zzprobe_110_x", {"dependency_type": "finish-to-start-next-day"})])
    TNAME = {tid["zzprobe_110_x"]: "A.x", tid["zzprobe_110_y"]: "A.y"}
    seen.update(tid.values())
    rows.append("=== template A: x, y; edge y on x finish-to-start-next-day")

    def state(label, sh, names):
        """names: {task id: label}. Grows as new Tasks appear. Prints Tasks, links, edges."""
        on = T.tasks_on(c, sh, ["content", "template_task", "sg_description"])
        T.adopt(made, on)
        for t in on:
            seen.add(t["id"])
            names.setdefault(t["id"], f"new{len(names)}")
        parts = []
        for t in on:
            tt = (T.rel(t, "template_task") or {}).get("id")
            parts.append(f"{names[t['id']]}->{TNAME.get(tt, tt)}")
        edges = T.deps_among(c, [t["id"] for t in on])
        es = [f"{names.get(T.rel(e, 'task')['id'])} on {names.get(T.rel(e, 'dependent_task')['id'])}#{e['id']}"
              for e in edges]
        per = {}
        for t in on:
            tt = (T.rel(t, "template_task") or {}).get("id")
            per[TNAME.get(tt, tt)] = per.get(TNAME.get(tt, tt), 0) + 1
        rows.append(f"  {label:<26} {len(on)} Tasks [{', '.join(parts)}]  per template task {per}  edges {es}")
        return on, edges

    def retired_link(i):
        r = c.post("/entity/tasks/_search", headers=T.ARR,
                   json={"filters": [["id", "is", i]], "fields": ["template_task", "entity"],
                         "options": {"return_only": "retired"}})
        if not r.ok:
            return T.errs(r)
        d = r.json()["data"]
        if not d:
            return "not listed as retired"
        tt = (T.rel(d[0], "template_task") or {}).get("id")
        return f"listed retired, template_task={TNAME.get(tt, tt)}"

    def delete(route, i):
        if route == "DELETE":
            r = c.delete(f"/entity/tasks/{i}")
            return f"DELETE -> {r.status_code} {len(r.content)} bytes"
        r = c.post("/entity/_batch", json={"requests": [{"request_type": "delete", "entity": "Task", "record_id": i}]})
        return f"_batch delete -> {r.status_code} {json.dumps(r.json().get('data')) if r.ok else T.errs(r)}"

    def revive(i):
        r = c.post(f"/entity/tasks/{i}", params={"revive": 1})
        return f"revive X -> {r.status_code} {json.dumps(r.json().get('meta')) if r.ok else T.errs(r)}"

    def write_template(sh):
        r1 = c.put(f"/entity/shots/{sh['id']}", json={"task_template": None})
        r2 = c.put(f"/entity/shots/{sh['id']}", json={"task_template": TT})
        return f"PUT task_template null -> {r1.status_code}, A -> {r2.status_code} {'' if r2.ok else T.errs(r2)}"

    for route in ("DELETE", "batch"):
        for order in ("template first", "revive first"):
            rows.append(f"\n=== {route}, {order}")
            sh = T.ref(T.post(c, made, "shots", {"project": P, "code": f"zzprobe_110_{route}_{order[0]}",
                                                 "task_template": TT}))
            on = T.tasks_on(c, sh, ["template_task"])
            T.adopt(made, on)
            by = {(T.rel(t, "template_task") or {}).get("id"): t["id"] for t in on}
            X, Y = by[tid["zzprobe_110_x"]], by[tid["zzprobe_110_y"]]
            names = {X: "X", Y: "Y"}
            _, e0 = state("created with A", sh, names)
            e0 = {e["id"] for e in e0}
            rows.append(f"  {delete(route, X)}")
            state("X retired", sh, names)
            rows.append(f"    X read with return_only retired: {retired_link(X)}")
            steps = (("tpl", "rev") if order == "template first" else ("rev", "tpl"))
            for s in steps:
                if s == "tpl":
                    rows.append(f"  {write_template(sh)}")
                    state("after template write", sh, names)
                else:
                    rows.append(f"  {revive(X)}")
                    _, es = state("after revive", sh, names)
                    rows.append(f"    original edge ids live again: {e0 <= {e['id'] for e in es}}")

rows.append("\n=== left clean?")
refs = [tref(i) for i in sorted(seen)]
left = {d["id"] for f in ("task", "dependent_task")
        for d in T.search(c, "task_dependencies", [[f, "in", refs]], ["task"])}
rows.append(f"  Tasks zzprobe_110* (site-wide, template tasks included): "
            f"{len(T.search(c, 'tasks', [['content', 'starts_with', 'zzprobe_110']], ['content']))}"
            f"  TaskDependency rows touching the {len(seen)} Tasks seen: {len(left)}"
            f"  TaskTemplates: {len(T.search(c, 'task_templates', [['code', 'starts_with', 'zzprobe_110']], ['code']))}"
            f"  Shots: {len(T.search(c, 'shots', [['project', 'is', P], ['code', 'starts_with', 'zzprobe_110']], ['code']))}")
rows.append(f"\n=== run: {time.monotonic() - T0:.1f}s wall, {CALLS[0]} calls (token fetch not counted)")

_lib.emit("110_template_task_after_revive", "\n".join(rows), env)
