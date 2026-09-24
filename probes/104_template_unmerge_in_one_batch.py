"""Q: does recipe 019's undo of a template merge give the same end state as ONE `_batch`?

Recipe 019 (probe 096) undoes a merge into template B with separate calls: the old `template_task` on each
claimed Task, then the old `task_template` on the entity, then DELETE the Tasks the merge made and the
merge's edges between old Tasks, then write the snapshot's fields back. Here the same sequence goes into
one `_batch` on a twin Shot, and the two end states are compared row by row, and against the snapshot.

Templates as in probe 096. A: comp, roto, lay; roto on comp. B: comp, lay (same content and step), paint;
lay on comp start-to-start 1, paint on lay. Four Shots:
  X, Y: created with A, then hand edits; merged into B; X undone by recipe 019's calls, Y by one batch.
  N1, N2: no template, hand-made comp and lay; merged into B; undone to null, N1 by calls, N2 by one batch.
The merges are recipe 020's batch (claims, null, B), one per Shot.

Negative control on Y first: the batch built by copying recipe 019's step 3 read before the batch runs,
so it also DELETEs B's lay-on-comp edge, which the batch's own `task_template` A write removes first.

Provisioned by the probe: both templates, the Shots and their Tasks, all deleted on exit. No operator
step. Writes only, in the sandbox, behind --write. Wall time and call count are printed.
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


c.request = counted  # get/post/put/delete and _lib.Created's deletes all go through request

if not _lib.writes_allowed():
    raise SystemExit("probe 104 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
s1, s2, s3 = ({"type": "Step", "id": ST[k]} for k in sorted(ST)[:3])
N = "zzprobe_104_"
FIELDS = ["content", "entity", "template_task", "sg_status_list", "sg_sort_order", "sg_description", "duration"]
KEEP = ["sg_sort_order", "sg_description", "duration"]
rows = []
names = {}

A_TASKS = {"comp": {"step": s1, "sg_sort_order": 10, "sg_description": "from A", "duration": 480},
           "roto": {"step": s2, "sg_sort_order": 20, "sg_description": "from A", "duration": 480},
           "lay": {"step": s3, "sg_sort_order": 30, "sg_description": "from A", "duration": 480}}
B_TASKS = {"comp": {"step": s1, "sg_sort_order": 110, "sg_description": "from B", "duration": 960},
           "lay": {"step": s3, "sg_sort_order": 130, "sg_description": "from B", "duration": 960},
           "paint": {"step": s2, "sg_sort_order": 140, "sg_description": "from B", "duration": 960}}


def upd(entity, rid, data):
    return {"request_type": "update", "entity": entity, "record_id": rid, "data": data}


def dele(entity, rid):
    return {"request_type": "delete", "entity": entity, "record_id": rid}


def tt_id(row, field):
    return (T.rel(row, field) or {}).get("id")


def state(shots):
    """Every Task, edge and task_template of these Shots, three reads."""
    tasks = T.search(c, "tasks", [["entity", "in", shots]], FIELDS)
    T.adopt(made, tasks)
    deps = T.deps_among(c, [t["id"] for t in tasks])
    sh = T.search(c, "shots", [["id", "in", [s["id"] for s in shots]]], ["task_template"])
    out = {}
    for s in shots:
        mine = sorted((t for t in tasks if tt_id(t, "entity") == s["id"]), key=lambda t: t["id"])
        ids = {t["id"] for t in mine}
        out[s["id"]] = {"tasks": mine, "deps": [d for d in deps if tt_id(d, "task") in ids],
                        "tt": next(tt_id(x, "task_template") for x in sh if x["id"] == s["id"])}
    return out


def norm(st):
    """A Shot's state as comparable rows: Task ids, fields, edges by content, the template."""
    by_id = {t["id"]: t["attributes"]["content"] for t in st["tasks"]}
    tasks = sorted((t["attributes"]["content"], names.get(tt_id(t, "template_task")),
                    t["attributes"]["sg_status_list"], *(t["attributes"][k] for k in KEEP))
                   for t in st["tasks"])
    deps = sorted((by_id.get(tt_id(d, "task")), by_id.get(tt_id(d, "dependent_task")),
                   d["attributes"]["dependency_type"], d["attributes"]["offset_days"]) for d in st["deps"])
    return {"template": names.get(("tt", st["tt"])), "tasks": tasks, "deps": deps,
            "task_ids": sorted(by_id), "dep_ids": sorted(d["id"] for d in st["deps"])}


def show(label, st):
    n = norm(st)
    rows.append(f"  {label}: task_template={n['template']}, {len(n['tasks'])} Tasks, {len(n['deps'])} edges")
    for t in n["tasks"]:
        rows.append(f"    {t[0]:<6} template_task={t[1]!s:<7} status={t[2]} order={t[3]} desc={t[4]!r} dur={t[5]}")
    for d in n["deps"]:
        rows.append(f"    dep {d[0]} on {d[1]} {d[2]} offset_days={d[3]}")


def compare(label, a, b, ids=True):
    """ids=False for twin Shots, whose rows are different rows by construction."""
    na, nb = norm(a), norm(b)
    diff = [k for k in na if na[k] != nb[k] and (ids or not k.endswith("_ids"))]
    rows.append(f"  {label}: {'identical' if not diff else 'DIFFER in ' + ', '.join(diff)}")
    for k in diff:
        rows.append(f"    {k}: {na[k]} | {nb[k]}")


def snapshot(st):
    return {"tt": st["tt"],
            "tasks": {t["id"]: {"template_task": T.rel(t, "template_task"),
                                **{k: t["attributes"][k] for k in KEEP}} for t in st["tasks"]},
            "deps": {d["id"] for d in st["deps"]}}


def ttref(i):
    return {"type": "TaskTemplate", "id": i} if i else None


def undo_calls(shot, snap):
    """Recipe 019, verbatim in its order: one call per write."""
    before = snap["tasks"]
    now = T.search(c, "tasks", [["entity", "is", shot]], ["template_task"])
    codes = []
    for t in now:
        old = before.get(t["id"])
        if old and tt_id(t, "template_task") != (old["template_task"] or {}).get("id"):
            codes.append(c.put(f"/entity/tasks/{t['id']}", json={"template_task": old["template_task"]}).status_code)
    codes.append(c.put(f"/entity/shots/{shot['id']}", json={"task_template": ttref(snap["tt"])}).status_code)
    for t in now:
        if t["id"] not in before:
            codes.append(c.delete(f"/entity/tasks/{t['id']}").status_code)
    for d in T.deps_among(c, list(before)):
        if d["id"] not in snap["deps"]:
            codes.append(c.delete(f"/entity/task_dependencies/{d['id']}").status_code)
    for i, old in before.items():
        codes.append(c.put(f"/entity/tasks/{i}", json={k: old[k] for k in KEEP}).status_code)
    return codes


def undo_batch(shot, snap, st, sweep_all):
    """The same writes as one batch, every id read before it runs (from `st`, the merged state).

    sweep_all: DELETE every edge between old Tasks that the snapshot lacks, as recipe 019's step 3 read
    would find it now. Otherwise skip those whose two ends both return to a template task, which the
    batch's own `task_template` write removes (probe 096); with a null template nothing removes them.
    """
    before = snap["tasks"]
    reqs = []
    for t in st["tasks"]:
        old = before.get(t["id"])
        if old and tt_id(t, "template_task") != (old["template_task"] or {}).get("id"):
            reqs.append(upd("Task", t["id"], {"template_task": old["template_task"]}))
    reqs.append(upd("Shot", shot["id"], {"task_template": ttref(snap["tt"])}))
    for t in st["tasks"]:
        if t["id"] not in before:
            reqs.append(dele("Task", t["id"]))
    for d in st["deps"]:
        down, up = tt_id(d, "task"), tt_id(d, "dependent_task")
        if d["id"] in snap["deps"] or down not in before or up not in before:
            continue   # kept, or retires with the Task deleted above (probe 089)
        server_removes = snap["tt"] and before[down]["template_task"] and before[up]["template_task"]
        if sweep_all or not server_removes:
            reqs.append(dele("TaskDependency", d["id"]))
    for i, old in before.items():
        reqs.append(upd("Task", i, {k: old[k] for k in KEEP}))
    r = c.post("/entity/_batch", json={"requests": reqs})
    kinds = [f"{q['request_type']} {q['entity']}" + (" task_template" if q["entity"] == "Shot" else "")
             for q in reqs]
    return r, kinds


with _lib.Created(c) as made:
    TTA, idsA = T.template(c, made, N + "ttA", A_TASKS, deps=[("roto", "comp", {})])
    TTB, idsB = T.template(c, made, N + "ttB", B_TASKS,
                           deps=[("lay", "comp", {"dependency_type": "start-to-start", "offset_days": 1}),
                                 ("paint", "lay", {})])
    names.update({("tt", TTA["id"]): "A", ("tt", TTB["id"]): "B", ("tt", None): None})
    names.update({i: f"A.{k}" for k, i in idsA.items()})
    names.update({i: f"B.{k}" for k, i in idsB.items()})

    X, Y = (T.ref(T.post(c, made, "shots", {"project": P, "code": N + k, "task_template": TTA})) for k in "XY")
    N1, N2 = (T.ref(T.post(c, made, "shots", {"project": P, "code": N + k})) for k in ("N1", "N2"))
    for sh in (N1, N2):
        T.post(c, made, "tasks", {"project": P, "entity": sh, "content": "comp", "step": s1,
                                  "sg_status_list": "ip", "sg_description": "hand"})
        T.post(c, made, "tasks", {"project": P, "entity": sh, "content": "lay", "step": s3, "sg_sort_order": 99})
    SHOTS = [X, Y, N1, N2]
    st = state(SHOTS)
    hand = []
    for sh in (X, Y):
        t = {x["attributes"]["content"]: x["id"] for x in st[sh["id"]]["tasks"]}
        hand += [upd("Task", t["comp"], {"sg_status_list": "ip", "sg_description": "hand"}),
                 upd("Task", t["lay"], {"sg_sort_order": 99}),
                 upd("Task", t["roto"], {"sg_description": "hand", "duration": 1440})]
    r = c.post("/entity/_batch", json={"requests": hand})
    rows.append(f"hand edits on X, Y (comp ip 'hand', lay order 99, roto 'hand' 1440) -> {r.status_code}")

    S0 = state(SHOTS)
    snaps = {s["id"]: snapshot(S0[s["id"]]) for s in SHOTS}
    rows.append("\n=== before the merge")
    show("X", S0[X["id"]])
    show("N1", S0[N1["id"]])
    compare("Y vs X", S0[Y["id"]], S0[X["id"]], ids=False)
    compare("N2 vs N1", S0[N2["id"]], S0[N1["id"]], ids=False)

    merge = []
    for sh in SHOTS:
        t = {x["attributes"]["content"]: x["id"] for x in S0[sh["id"]]["tasks"]}
        merge += [upd("Task", t[k], {"template_task": {"type": "Task", "id": idsB[k]}}) for k in ("comp", "lay")]
        merge += [upd("Shot", sh["id"], {"task_template": None}), upd("Shot", sh["id"], {"task_template": TTB})]
    r = c.post("/entity/_batch", json={"requests": merge})
    rows.append(f"\n=== merge all four into B (recipe 020, one batch) -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    S1 = state(SHOTS)
    show("X", S1[X["id"]])
    show("N1", S1[N1["id"]])
    compare("Y vs X", S1[Y["id"]], S1[X["id"]], ids=False)
    compare("N2 vs N1", S1[N2["id"]], S1[N1["id"]], ids=False)

    rows.append("\n=== undo X, N1 by recipe 019's separate calls")
    rows.append(f"  X  codes {undo_calls(X, snaps[X['id']])}")
    rows.append(f"  N1 codes {undo_calls(N1, snaps[N1['id']])}")

    rows.append("\n=== negative control: Y, one batch that also DELETEs every edge recipe 019's step 3 would sweep")
    r, kinds = undo_batch(Y, snaps[Y["id"]], S1[Y["id"]], sweep_all=True)
    rows.append(f"  requests: {kinds}")
    rows.append(f"  -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    after = state([Y])
    compare("Y after the rejected batch vs Y merged", after[Y["id"]], S1[Y["id"]])

    rows.append("\n=== undo Y, N2 by one batch each")
    for label, sh in (("Y", Y), ("N2", N2)):
        r, kinds = undo_batch(sh, snaps[sh["id"]], S1[sh["id"]], sweep_all=False)
        rows.append(f"  {label} requests: {kinds}")
        rows.append(f"  {label} -> {r.status_code} {T.errs(r) if not r.ok else ''}")

    S2 = state(SHOTS)
    rows.append("\n=== after the undo")
    show("X (calls)", S2[X["id"]])
    show("N1 (calls)", S2[N1["id"]])
    compare("Y (batch) vs X (calls)", S2[Y["id"]], S2[X["id"]], ids=False)
    compare("N2 (batch) vs N1 (calls)", S2[N2["id"]], S2[N1["id"]], ids=False)
    for label, sh in (("X", X), ("Y", Y), ("N1", N1), ("N2", N2)):
        compare(f"{label} after vs {label} before the merge (Task and edge ids too)", S2[sh["id"]], S0[sh["id"]])
    all_task_ids = [i for s in (S0, S1) for v in s.values() for i in (t["id"] for t in v["tasks"])]
    tpl_task_ids = list(idsA.values()) + list(idsB.values())

rows.append("\n=== left clean?")
rows.append(f"  Shots {N}*: {len(T.search(c, 'shots', [['project', 'is', P], ['code', 'starts_with', N]], ['code']))}")
rows.append(f"  Tasks on the Shots: {len(T.search(c, 'tasks', [['entity', 'in', SHOTS]], ['content']))}")
rows.append(f"  Tasks by id (Shot and template tasks): "
            f"{len(T.search(c, 'tasks', [['id', 'in', all_task_ids + tpl_task_ids]], ['content']))}")
rows.append(f"  TaskDependency rows on any of them: {len(T.deps_among(c, all_task_ids + tpl_task_ids))}")
rows.append(f"  templates {N}*: {len(T.search(c, 'task_templates', [['code', 'starts_with', N]], ['code']))}")
rows.append(f"\nwall {time.monotonic() - T0:.1f}s, {CALLS[0]} calls")

_lib.emit("104_template_unmerge_in_one_batch", "\n".join(rows), env)
