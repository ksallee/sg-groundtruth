"""Q: when the undo of a merge writes `task_template` back to the old template A (recipes 019, 022),
which edges does that write erase: an edge re-created after the merge into a Task going back to A, a
mixed edge (one end back on A, the other a Task the merge made or an extra), an edge between two
A-linked Tasks that A lacks?

Templates as in probe 104. A: comp, roto, lay; roto on comp. B: comp, lay (same content and step), paint;
lay on comp start-to-start 1, paint on lay. Two twin Shots, M and W, each made with A plus two extra
hand-made Tasks x, y (unlinked), and three hand edges before the merge:

  comp on x   A-linked downstream, extra upstream (the merge erases it, probe 109)
  roto on x   roto is never claimed by B; A-linked downstream, extra upstream
  roto on lay both ends A-linked, A lacks the edge

Merge: recipe 020's batch (claims comp, lay to B; null; B). Then, as a user would after the merge:

  R1 comp on x   re-created (the merge erased it), new id
  R2 roto on paint  A-linked downstream, upstream the Task the merge made (to be deleted)
  R3 y on lay    extra downstream, upstream a Task going back to A

Undo M by recipe 022's batch as written, then (if it is rejected) by the same batch leaving out the
edges whose downstream end goes back to an A template task. Undo W by recipe 019's separate calls,
reading the edges after each step, which is what attributes an erase to the `task_template` write.

Provisioned by the probe: both templates, the Shots, Tasks and edges, deleted by `_lib.Created`,
failure included. No operator step. Writes only, in the sandbox, behind --write. Wall time and call
count are printed.
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
    raise SystemExit("probe 111 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
s1, s2, s3 = ({"type": "Step", "id": ST[k]} for k in sorted(ST)[:3])
N = "zzprobe_111_"
KEEP = ["sg_sort_order", "sg_description", "duration"]
rows = []
name = {}
seen = set()
known = {}   # Shot id -> every Task id ever read on it, so an edge read needs no Task read

A_TASKS = {"comp": {"step": s1, "sg_sort_order": 10, "duration": 480},
           "roto": {"step": s2, "sg_sort_order": 20, "duration": 480},
           "lay": {"step": s3, "sg_sort_order": 30, "duration": 480}}
B_TASKS = {"comp": {"step": s1, "sg_sort_order": 110, "duration": 960},
           "lay": {"step": s3, "sg_sort_order": 130, "duration": 960},
           "paint": {"step": s2, "sg_sort_order": 140, "duration": 960}}


def link(row, f):
    return T.rel(row, f)


def tid(row, f):
    return (T.rel(row, f) or {}).get("id")


def upd(entity, rid, data):
    return {"request_type": "update", "entity": entity, "record_id": rid, "data": data}


def dele(entity, rid):
    return {"request_type": "delete", "entity": entity, "record_id": rid}


def dep(down, up):
    return {"task": {"type": "Task", "id": down}, "dependent_task": {"type": "Task", "id": up}}


def tasks(shot):
    got = T.tasks_on(c, shot, ["content", "template_task"] + KEEP)
    T.adopt(made, got)
    for t in got:
        name.setdefault(t["id"], t["attributes"]["content"].replace(N, ""))
        known.setdefault(shot["id"], set()).add(t["id"])
    return got


def edges(shot, label):
    """Every edge with a downstream Task on the Shot, logged as 'down on up #id'.

    Edges are not registered with `_lib.Created`: the Task deletes retire them (probe 089), and the
    left-clean check reads every id seen.
    """
    got = T.deps_among(c, sorted(known[shot["id"]]))
    for g in got:
        seen.add(g["id"])
    rows.append(f"  {label}: " + ", ".join(sorted(
        f"{name.get(tid(g, 'task'))} on {name.get(tid(g, 'dependent_task'))} #{g['id']}" for g in got)))
    return got


def by_name(shot):
    return {t["attributes"]["content"].replace(N, ""): t["id"] for t in tasks(shot)}


# recipe 019's snapshot, adapted to the probe's helpers
def snapshot(shot):
    sh = c.get(f"/entity/shots/{shot['id']}", params={"fields": "task_template"}).json()["data"]
    ts = T.search(c, "tasks", [["entity", "is", shot]], KEEP + ["template_task"])
    ids = [{"type": "Task", "id": t["id"]} for t in ts]
    deps = T.search(c, "task_dependencies", [["task", "in", ids]], ["task"])
    return {"task_template": link(sh, "task_template"),
            "tasks": {t["id"]: {**{k: t["attributes"][k] for k in KEEP},
                                "template_task": link(t, "template_task")} for t in ts},
            "deps": {d["id"] for d in deps}}


# recipe 020's apply_template, verbatim in its logic
def apply_template(entity, template_id):
    tpl_ref = {"type": "TaskTemplate", "id": template_id}
    tpl = T.search(c, "tasks", [["task_template", "is", tpl_ref]], ["content", "step"])
    have = T.search(c, "tasks", [["entity", "is", entity]], ["content", "step", "template_task"])

    def key(t):
        return t["attributes"]["content"], tid(t, "step")
    mine = {t["id"] for t in tpl}
    taken = {tid(t, "template_task") for t in have}
    free = {key(t): t for t in have if tid(t, "template_task") not in mine}
    reqs = [upd("Task", free[key(t)]["id"], {"template_task": {"type": "Task", "id": t["id"]}})
            for t in tpl if key(t) in free and t["id"] not in taken]
    for value in (None, tpl_ref):
        reqs.append(upd(entity["type"], entity["id"], {"task_template": value}))
    r = c.post("/entity/_batch", json={"requests": reqs})
    return r, len(reqs) - 2


# recipe 022's undo_merge; skip_down=True is the variant this probe tests
def undo_batch(entity, snap, skip_down=False):
    before = snap["tasks"]
    now = T.search(c, "tasks", [["entity", "is", entity]], ["template_task"])
    ids = [{"type": "Task", "id": t["id"]} for t in now]
    deps = T.search(c, "task_dependencies", [["task", "in", ids]], ["task", "dependent_task"])
    reqs = []
    for t in now:
        old = before.get(t["id"])
        if old and tid(t, "template_task") != (old["template_task"] or {}).get("id"):
            reqs.append(upd("Task", t["id"], {"template_task": old["template_task"]}))
    reqs.append(upd(entity["type"], entity["id"], {"task_template": snap["task_template"]}))
    for t in now:
        if t["id"] not in before:
            reqs.append(dele("Task", t["id"]))
    dels = []
    for d in deps:
        down, up = tid(d, "task"), tid(d, "dependent_task")
        if d["id"] in snap["deps"] or down not in before or up not in before:
            continue
        if skip_down:
            removed = snap["task_template"] and before[down]["template_task"]
        else:
            removed = snap["task_template"] and before[down]["template_task"] and before[up]["template_task"]
        if not removed:
            reqs.append(dele("TaskDependency", d["id"]))
            dels.append(f"{name.get(down)} on {name.get(up)} #{d['id']}")
    for i, old in before.items():
        reqs.append(upd("Task", i, {k: old[k] for k in KEEP}))
    r = c.post("/entity/_batch", json={"requests": reqs})
    return r, dels


# recipe 019's undo_merge, with an edge read after each step
def undo_calls(shot, snap):
    before = snap["tasks"]
    now = T.search(c, "tasks", [["entity", "is", shot]], ["template_task"])
    codes = []
    for t in now:
        old = before.get(t["id"])
        if old and tid(t, "template_task") != (old["template_task"] or {}).get("id"):
            codes.append(c.put(f"/entity/tasks/{t['id']}", json={"template_task": old["template_task"]}).status_code)
    rows.append(f"  step 1 claims back to A -> {codes}")
    edges(shot, "edges after step 1")
    r = c.put(f"/entity/shots/{shot['id']}", json={"task_template": snap["task_template"]})
    rows.append(f"  step 2 PUT Shot task_template=A -> {r.status_code} {'' if r.ok else T.errs(r)}")
    edges(shot, "edges after step 2")
    codes = []
    for t in now:
        if t["id"] not in before:
            codes.append(("Task", name.get(t["id"]), c.delete(f"/entity/tasks/{t['id']}").status_code))
    for d in T.deps_among(c, list(before)):
        if d["id"] not in snap["deps"]:
            codes.append((f"{name.get(tid(d, 'task'))} on {name.get(tid(d, 'dependent_task'))} #{d['id']}",
                          c.delete(f"/entity/task_dependencies/{d['id']}").status_code))
    rows.append(f"  step 3 DELETEs -> {codes}")
    edges(shot, "edges after step 3")
    codes = [c.put(f"/entity/tasks/{i}", json={k: old[k] for k in KEEP}).status_code for i, old in before.items()]
    rows.append(f"  step 4 field writes -> {codes}")


with _lib.Created(c) as made:
    TTA, idsA = T.template(c, made, N + "ttA", {N + k: v for k, v in A_TASKS.items()},
                           deps=[(N + "roto", N + "comp", {})])
    TTB, idsB = T.template(c, made, N + "ttB", {N + k: v for k, v in B_TASKS.items()},
                           deps=[(N + "lay", N + "comp", {"dependency_type": "start-to-start", "offset_days": 1}),
                                 (N + "paint", N + "lay", {})])
    tpl_task_ids = list(idsA.values()) + list(idsB.values())
    rows.append("A: comp, roto, lay; roto on comp.  B: comp, lay, paint; lay on comp SS+1, paint on lay")

    M, W = (T.ref(T.post(c, made, "shots", {"project": P, "code": N + k, "task_template": TTA})) for k in "MW")
    pre = {}
    for sh in (M, W):
        for n in ("x", "y"):
            T.post(c, made, "tasks", {"project": P, "entity": sh, "content": N + n})
        t = by_name(sh)
        pre[sh["id"]] = {k: c.post("/entity/task_dependencies", json=dep(t[d], t[u])).json()["data"]["id"]
                         for k, (d, u) in {"comp on x": ("comp", "x"), "roto on x": ("roto", "x"),
                                           "roto on lay": ("roto", "lay")}.items()}
    rows.append("M, W made with A, + x, y unlinked, + hand edges comp on x, roto on x, roto on lay")
    snaps = {sh["id"]: snapshot(sh) for sh in (M, W)}
    for label, sh in (("M", M), ("W", W)):
        for g in edges(sh, f"{label} edges before the merge"):
            if (name[tid(g, "task")], name[tid(g, "dependent_task")]) == ("roto", "comp"):
                pre[sh["id"]]["A roto on comp"] = g["id"]

    rows.append("\n=== merge (recipe 020 batch), per Shot")
    tn = {}
    for label, sh in (("M", M), ("W", W)):
        r, n = apply_template(sh, TTB["id"])
        rows.append(f"  {label}: {n} claims -> {r.status_code} {'' if r.ok else T.errs(r)}")
        tn[sh["id"]] = by_name(sh)
        edges(sh, f"{label} edges after the merge")

    rows.append("\n=== after the merge, by hand: R1 comp on x (re-created), R2 roto on paint, R3 y on lay")
    post, merged = {}, {}
    for label, sh in (("M", M), ("W", W)):
        t = tn[sh["id"]]
        post[sh["id"]] = {}
        for k, (d, u) in {"R1 comp on x": ("comp", "x"), "R2 roto on paint": ("roto", "paint"),
                          "R3 y on lay": ("y", "lay")}.items():
            r = c.post("/entity/task_dependencies", json=dep(t[d], t[u]))
            rows.append(f"  {label} POST {k} -> {r.status_code} {'' if r.ok else T.errs(r)}")
            if r.ok:
                post[sh["id"]][k] = r.json()["data"]["id"]
        merged[sh["id"]] = sorted(g["id"] for g in edges(sh, f"{label} edges before the undo"))

    rows.append("\n=== W: undo by recipe 019's separate calls, edges read after each step")
    undo_calls(W, snaps[W["id"]])

    rows.append("\n=== M: undo by recipe 022's batch as written")
    r, dels = undo_batch(M, snaps[M["id"]])
    rows.append(f"  edge DELETEs in the batch: {dels}")
    rows.append(f"  -> {r.status_code} {'' if r.ok else T.errs(r)}")
    after = sorted(g["id"] for g in edges(M, "M edges now"))
    rows.append(f"  M edge ids unchanged from before the undo: {after == merged[M['id']]}")
    if not r.ok:
        rows.append("\n=== M: the same batch, leaving out edges whose downstream end goes back to an A task")
        r, dels = undo_batch(M, snaps[M["id"]], skip_down=True)
        rows.append(f"  edge DELETEs in the batch: {dels}")
        rows.append(f"  -> {r.status_code} {'' if r.ok else T.errs(r)}")
        edges(M, "M edges after the undo")

    rows.append("\n=== M: every edge id seen on M, GET and GET options[return_only]=retired")
    for k, i in list(pre[M["id"]].items()) + list(post[M["id"]].items()):
        live = c.get(f"/entity/task_dependencies/{i}").status_code
        ret = c.get(f"/entity/task_dependencies/{i}", params={"options[return_only]": "retired"}).status_code
        rows.append(f"  {k:<18} #{i}: GET {live}, retired {ret}")
    sh_tt = {s["id"]: tid(s, "task_template") for s in T.search(c, "shots", [["id", "in", [M["id"], W["id"]]]],
                                                               ["task_template"])}
    rows.append(f"  task_template M={'A' if sh_tt[M['id']] == TTA['id'] else sh_tt[M['id']]}, "
                f"W={'A' if sh_tt[W['id']] == TTA['id'] else sh_tt[W['id']]}")
    for label, sh in (("M", M), ("W", W)):
        rows.append(f"  {label} Tasks: " + ", ".join(
            f"{t['attributes']['content'].replace(N, '')}->"
            f"{'A' if tid(t, 'template_task') in idsA.values() else tid(t, 'template_task')}"
            for t in tasks(sh)))
    all_task_ids = sorted(name)

rows.append("\n=== left clean?")
rows.append(f"  Shots {N}*: {len(T.search(c, 'shots', [['project', 'is', P], ['code', 'starts_with', N]], ['code']))}")
rows.append(f"  Tasks by id (Shot and template tasks): "
            f"{len(T.search(c, 'tasks', [['id', 'in', all_task_ids + tpl_task_ids]], ['content']))}")
rows.append(f"  Tasks {N}*: {len(T.search(c, 'tasks', [['content', 'starts_with', N]], ['content']))}")
rows.append(f"  TaskDependency rows by id: {len(T.search(c, 'task_dependencies', [['id', 'in', sorted(seen)]], ['task']))}")
rows.append(f"  TaskDependency rows on any Task: {len(T.deps_among(c, all_task_ids + tpl_task_ids))}")
rows.append(f"  templates {N}*: {len(T.search(c, 'task_templates', [['code', 'starts_with', N]], ['code']))}")
rows.append(f"\nwall {time.monotonic() - T0:.1f}s, {CALLS[0]} calls")

_lib.emit("111_template_undo_outside_edge", "\n".join(rows), env)
