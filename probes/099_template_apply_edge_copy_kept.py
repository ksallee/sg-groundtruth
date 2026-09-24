"""Q: recipe 015's merge apply copies a template's TaskDependency edges onto claimed Tasks (probe 092
showed both ends newly claimed in the same run). Does it also copy an edge when:

  (1) one end was already linked to its template task before this run (kept, not re-claimed) and the
      other end is newly claimed this run,
  (2) both ends were already linked before this run (kept + kept) but the edge itself is missing, and
  (3) one end is a Task the apply itself creates, the other kept?

One template `tt`: two template tasks `x`, `y`, one edge `y` depends on `x`. One Shot per case, each
pre-loaded with Tasks in the state the case names, then `PUT task_template` null then `tt` (recipe 015).
"kept" means `template_task` was set to the template task's id at Task creation, standing in for a Task
a prior apply already claimed; "claimed" means the Task starts unlinked and the probe's own `_batch`
claim (recipe 015 step 1) points it at the template task in this run.

Preconditions: none from an operator. The probe provisions every row it reads (3 Shots, 5 hand-made
Tasks, one 2-task template and its edge) and `_lib.Created` deletes them, failure included.

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
    raise SystemExit("probe 099 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
step_x, step_y = (ST[k] for k in sorted(ST)[:2])


def task_ref(i):
    return {"type": "Task", "id": i}


def edge_state(label, ids):
    """ids: {name: task_id or None}. Print each Task's template_task and any edge among them."""
    present = {n: i for n, i in ids.items() if i is not None}
    got = {t["id"]: t for t in T.search(c, "tasks", [["id", "in", list(present.values())]],
                                         ["content", "template_task"])} if present else {}
    rows.append(f"  {label}")
    for n, i in ids.items():
        if i is None:
            rows.append(f"    {n:<3} not yet created")
            continue
        tt = T.rel(got[i], "template_task")
        rows.append(f"    {n:<3} id={i} template_task={'set' if tt else None}")
    edges = T.deps_among(c, list(present.values())) if present else []
    nm = {v: k for k, v in present.items()}
    if not edges:
        rows.append("    edge: none")
    for e in edges:
        a = e["attributes"]
        rows.append(f"    edge: {nm.get(T.rel(e, 'task')['id'])} on {nm.get(T.rel(e, 'dependent_task')['id'])} "
                    f"{a['dependency_type']} offset_days={a['offset_days']}")
    return edges


with _lib.Created(c) as made:
    # ---- the template: x, y, edge y depends on x ----
    TT, tids = T.template(c, made, "zzprobe_099_tt",
                          {"zzprobe_099_x": {"step": {"type": "Step", "id": step_x}},
                           "zzprobe_099_y": {"step": {"type": "Step", "id": step_y}}},
                          [("zzprobe_099_y", "zzprobe_099_x", {"dependency_type": "finish-to-start-next-day"})])
    rows.append(f"=== template zzprobe_099_tt: x@step{step_x}, y@step{step_y}, edge y on x finish-to-start-next-day")

    def shot(code):
        return T.ref(T.post(c, made, "shots", {"project": P, "code": code}))

    def hand_task(sh, name, kept_as=None):
        """A hand-made Task matching template task `name`. kept_as, if given, is the template task id
        to set as template_task at create time — simulating a Task a prior apply already claimed."""
        body = {"project": P, "entity": sh, "content": f"zzprobe_099_{name}",
                "step": {"type": "Step", "id": step_x if name == "x" else step_y}}
        if kept_as is not None:
            body["template_task"] = task_ref(kept_as)
        return T.post(c, made, "tasks", body)["id"]

    def apply(sh):
        r1 = c.put(f"/entity/shots/{sh['id']}", json={"task_template": None})
        r2 = c.put(f"/entity/shots/{sh['id']}", json={"task_template": TT})
        rows.append(f"  PUT task_template=null -> {r1.status_code}; PUT task_template=tt -> {r2.status_code} "
                    f"{T.errs(r2) if not r2.ok else ''}")

    # ---- case 1: x kept (already linked before this run), y hand-made then claimed this run ----
    rows.append("\n=== case 1: x kept, y claimed this run")
    sh1 = shot("zzprobe_099_shot1")
    x1 = hand_task(sh1, "x", kept_as=tids["zzprobe_099_x"])
    y1 = hand_task(sh1, "y")  # unlinked; will be claimed
    edge_state("before", {"x": x1, "y": y1})
    claim = [{"request_type": "update", "entity": "Task", "record_id": y1,
              "data": {"template_task": task_ref(tids["zzprobe_099_y"])}}]
    r = c.post("/entity/_batch", json={"requests": claim})
    rows.append(f"  _batch claim y.template_task -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    edge_state("after claim, before apply", {"x": x1, "y": y1})
    apply(sh1)
    on1 = T.tasks_on(c, sh1, ["content"])
    T.adopt(made, on1)
    rows.append(f"  Tasks on Shot1: {len(on1)} (2 pre-made)")
    edge_state("after", {"x": x1, "y": y1})

    # ---- case 2: x kept, y kept (both already linked before this run), edge missing on site ----
    rows.append("\n=== case 2: x kept, y kept, no edge between them beforehand")
    sh2 = shot("zzprobe_099_shot2")
    x2 = hand_task(sh2, "x", kept_as=tids["zzprobe_099_x"])
    y2 = hand_task(sh2, "y", kept_as=tids["zzprobe_099_y"])
    edge_state("before", {"x": x2, "y": y2})
    apply(sh2)
    on2 = T.tasks_on(c, sh2, ["content"])
    T.adopt(made, on2)
    rows.append(f"  Tasks on Shot2: {len(on2)} (2 pre-made, both already linked, none should be claimed)")
    edge_state("after", {"x": x2, "y": y2})

    # ---- case 3: x kept, y absent -> the apply creates y ----
    rows.append("\n=== case 3: x kept, y has no Task on the Shot at all (apply creates it)")
    sh3 = shot("zzprobe_099_shot3")
    x3 = hand_task(sh3, "x", kept_as=tids["zzprobe_099_x"])
    edge_state("before", {"x": x3, "y": None})
    apply(sh3)
    on3 = T.tasks_on(c, sh3, ["content"])
    T.adopt(made, on3)
    rows.append(f"  Tasks on Shot3: {len(on3)} (1 pre-made + however many the apply created)")
    y3 = next((t["id"] for t in on3 if t["attributes"]["content"] == "zzprobe_099_y"), None)
    edge_state("after", {"x": x3, "y": y3})
    seen = sorted({*tids.values(), x1, y1, x2, y2, x3, *(t["id"] for t in on1 + on2 + on3)})

rows.append("\n=== left clean?")
rows.append(f"  Tasks zzprobe_099* (site-wide, template tasks included): "
            f"{len(T.search(c, 'tasks', [['content', 'starts_with', 'zzprobe_099']], ['content']))}")
refs = [task_ref(i) for i in seen]
left = {d["id"] for f in ("task", "dependent_task")
        for d in T.search(c, "task_dependencies", [[f, "in", refs]], ["task"])}
rows.append(f"  TaskDependency rows touching any of the {len(seen)} Tasks seen: {len(left)}")
rows.append(f"  TaskTemplates zzprobe_099*: "
            f"{len(T.search(c, 'task_templates', [['code', 'starts_with', 'zzprobe_099']], ['code']))}")
rows.append(f"  Shots zzprobe_099*: "
            f"{len(T.search(c, 'shots', [['project', 'is', P], ['code', 'starts_with', 'zzprobe_099']], ['code']))}")
rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")

_lib.emit("099_template_apply_edge_copy_kept", "\n".join(rows), env)
