"""Q: before a merge, two Tasks on one Shot both point `template_task` at old template A's task x (the site
allows it, probe 106). The merge into B unlinks the loser (`template_task` null) and claims the winner
for B.x (recipe 020). The undo (recipe 022's order) writes both old links back, both at A.x again, then
the Shot's `task_template` A. Which of the two does A's apply re-sync and wire, is that pick stable,
does it create anything, and does the end state equal the pre-merge one?

Template A: w, x, y on three steps; x on w, y on x (finish-to-start-next-day). B: x (same content and
step as A.x), z; z on x. Each field A and B set differs, so a re-sync is visible.

Three double Shots D1, D2, D3: created with A (w, xa, y and A's 2 edges generated), xa hand-edited
(desc "hand-a", order 55), then xb POSTed on x's step with template_task A.x, content "x_hand",
desc "hand-b", order 99, duration 1440. Control C: the same without xb.
Merge, one batch per Shot: [xb template_task null (D only), xa template_task B.x, Shot null, Shot B].
Undo, recipe 022 split in two batches so the apply's pick can be read before the field writes erase it:
  1: [xa, xb template_task A.x, Shot task_template A, DELETE z, edge DELETEs by recipe 022's rule]
     D3 only: xb's link goes after the Shot write, in the same batch (the proposed fix)
  2: the snapshot's content, sg_sort_order, sg_description, duration on every old Task.
Read after the merge, after batch 1 and after batch 2; compare with the pre-merge read (ids included).

Provisioned by the probe: both templates, the 4 Shots and their Tasks, all deleted on exit, failure
included. No operator step. Writes only, in the sandbox, behind --write. Wall time and call count print.
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
    raise SystemExit("probe 112 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
s1, s2, s3 = ({"type": "Step", "id": ST[k]} for k in sorted(ST)[:3])
N = "zzprobe_112_"
KEEP = ["content", "sg_sort_order", "sg_description", "duration"]
FIELDS = ["entity", "template_task", "sg_status_list", *KEEP]
FT = {"dependency_type": "finish-to-start-next-day"}
rows = []
names = {}

A_TASKS = {"w": {"step": s1, "sg_sort_order": 10, "sg_description": "A.w", "duration": 480},
           "x": {"step": s2, "sg_sort_order": 20, "sg_description": "A.x", "duration": 480},
           "y": {"step": s3, "sg_sort_order": 30, "sg_description": "A.y", "duration": 480}}
B_TASKS = {"x": {"step": s2, "sg_sort_order": 120, "sg_description": "B.x", "duration": 960},
           "z": {"step": s3, "sg_sort_order": 140, "sg_description": "B.z", "duration": 960}}


def upd(entity, rid, data):
    return {"request_type": "update", "entity": entity, "record_id": rid, "data": data}


def dele(entity, rid):
    return {"request_type": "delete", "entity": entity, "record_id": rid}


def rid(row, field):
    return (T.rel(row, field) or {}).get("id")


def state(shots):
    tasks = T.search(c, "tasks", [["entity", "in", shots]], FIELDS)
    T.adopt(made, tasks)
    deps = T.deps_among(c, [t["id"] for t in tasks])
    sh = T.search(c, "shots", [["id", "in", [s["id"] for s in shots]]], ["task_template"])
    out = {}
    for s in shots:
        mine = sorted((t for t in tasks if rid(t, "entity") == s["id"]), key=lambda t: t["id"])
        ids = {t["id"] for t in mine}
        out[s["id"]] = {"tasks": mine, "deps": [d for d in deps if rid(d, "task") in ids],
                        "tt": next(rid(x, "task_template") for x in sh if x["id"] == s["id"])}
    return out


def label(i):
    return names.get(i, f"new#{i}")


def norm(st):
    tasks = sorted((label(t["id"]), t["id"], names.get(rid(t, "template_task")), t["attributes"]["sg_status_list"],
                    *(t["attributes"][k] for k in KEEP)) for t in st["tasks"])
    deps = sorted((label(rid(d, "task")), label(rid(d, "dependent_task")), d["attributes"]["dependency_type"],
                   d["id"]) for d in st["deps"])
    return {"template": names.get(("tt", st["tt"])), "tasks": tasks, "deps": deps}


def show(tag, st):
    n = norm(st)
    rows.append(f"  {tag}: task_template={n['template']}, {len(n['tasks'])} Tasks, {len(n['deps'])} edges")
    for t in n["tasks"]:
        rows.append(f"    {t[0]:<4} template_task={t[2]!s:<5} {t[3]} content={t[4]} order={t[5]} desc={t[6]} dur={t[7]}")
    rows.append("    edges: " + ", ".join(f"{d[0]} on {d[1]} #{d[3] - DBASE}" for d in n["deps"]))


def compare(tag, a, b):
    na, nb = norm(a), norm(b)
    diff = [k for k in na if na[k] != nb[k]]
    rows.append(f"  {tag}: {'identical (Task ids, links, fields, edge ids)' if not diff else 'DIFFER in ' + ', '.join(diff)}")
    for k in diff:
        rows.append(f"    {k}: -{sorted(set(na[k]) - set(nb[k])) if k != 'template' else na[k]}"
                    f" +{sorted(set(nb[k]) - set(na[k])) if k != 'template' else nb[k]}")


with _lib.Created(c) as made:
    TTA, idsA = T.template(c, made, N + "ttA", {N + k: v for k, v in A_TASKS.items()},
                           deps=[(N + "x", N + "w", FT), (N + "y", N + "x", FT)])
    TTB, idsB = T.template(c, made, N + "ttB", {N + k: v for k, v in B_TASKS.items()},
                           deps=[(N + "z", N + "x", FT)])
    idsA = {k[len(N):]: v for k, v in idsA.items()}
    idsB = {k[len(N):]: v for k, v in idsB.items()}
    names.update({("tt", TTA["id"]): "A", ("tt", TTB["id"]): "B", ("tt", None): None})
    names.update({i: f"A.{k}" for k, i in idsA.items()})
    names.update({i: f"B.{k}" for k, i in idsB.items()})
    tdeps = T.deps_among(c, list(idsA.values()) + list(idsB.values()))
    DBASE = min(d["id"] for d in tdeps)

    D1, D2, D3, C = (T.ref(T.post(c, made, "shots", {"project": P, "code": N + k, "task_template": TTA}))
                     for k in ("D1", "D2", "D3", "C"))
    SHOTS = [D1, D2, D3, C]
    TAGS = ((D1, "D1"), (D2, "D2"), (D3, "D3"), (C, "C"))
    g = state(SHOTS)
    tid = {}
    hand = []
    for sh, tag in TAGS:
        t = {x["attributes"]["content"][len(N):]: x["id"] for x in g[sh["id"]]["tasks"]}
        names.update({t["w"]: "w", t["x"]: "xa", t["y"]: "y"})
        tid[sh["id"]] = {"xa": t["x"]}
        hand.append(upd("Task", t["x"], {"sg_description": "hand-a", "sg_sort_order": 55}))
        if tag != "C":
            xb = T.post(c, made, "tasks", {"project": P, "entity": sh, "content": N + "x_hand", "step": s2,
                                           "template_task": {"type": "Task", "id": idsA["x"]},
                                           "sg_description": "hand-b", "sg_sort_order": 99, "duration": 1440})
            names[xb["id"]] = "xb"
            tid[sh["id"]]["xb"] = xb["id"]
    r = c.post("/entity/_batch", json={"requests": hand})
    rows.append(f"A: w, x, y; x on w, y on x.  B: x (same content, step), z; z on x.  hand edits -> {r.status_code}")

    S0 = state(SHOTS)
    snaps = {s["id"]: {"tt": S0[s["id"]]["tt"],
                       "tasks": {t["id"]: {"template_task": T.rel(t, "template_task"),
                                           **{k: t["attributes"][k] for k in KEEP}} for t in S0[s["id"]]["tasks"]},
                       "deps": {d["id"] for d in S0[s["id"]]["deps"]}} for s in SHOTS}
    rows.append("\n=== before the merge")
    show("D1", S0[D1["id"]])
    show("C", S0[C["id"]])

    merge = []
    for sh in SHOTS:
        if "xb" in tid[sh["id"]]:
            merge.append(upd("Task", tid[sh["id"]]["xb"], {"template_task": None}))
        merge += [upd("Task", tid[sh["id"]]["xa"], {"template_task": {"type": "Task", "id": idsB["x"]}}),
                  upd("Shot", sh["id"], {"task_template": None}), upd("Shot", sh["id"], {"task_template": TTB})]
    r = c.post("/entity/_batch", json={"requests": merge})
    rows.append(f"\n=== merge into B, one batch [xb null, xa B.x, Shot null, Shot B] x3 -> {r.status_code} "
                f"{T.errs(r) if not r.ok else ''}")
    S1 = state(SHOTS)
    for t in (t for v in S1.values() for t in v["tasks"] if t["id"] not in names):
        names[t["id"]] = "z"
    show("D1", S1[D1["id"]])

    rows.append("\n=== undo batch 1: old links back (xa, xb both A.x), Shot A, DELETE z, recipe 022's edge rule")
    for sh, tag in TAGS:
        snap, st = snaps[sh["id"]], S1[sh["id"]]
        before = snap["tasks"]
        reqs = []
        late = []
        for t in st["tasks"]:
            old = before.get(t["id"])
            if old and rid(t, "template_task") != (old["template_task"] or {}).get("id"):
                q = upd("Task", t["id"], {"template_task": old["template_task"]})
                # D3: the loser, which held no edge before the merge, is relinked after the Shot write
                (late if tag == "D3" and t["id"] == tid[sh["id"]]["xb"] else reqs).append(q)
        reqs.append(upd("Shot", sh["id"], {"task_template": TTA}))
        reqs += late
        reqs += [dele("Task", t["id"]) for t in st["tasks"] if t["id"] not in before]
        for d in st["deps"]:
            down, up = rid(d, "task"), rid(d, "dependent_task")
            if d["id"] in snap["deps"] or down not in before or up not in before:
                continue
            if not (snap["tt"] and before[down]["template_task"] and before[up]["template_task"]):
                reqs.append(dele("TaskDependency", d["id"]))
        r = c.post("/entity/_batch", json={"requests": reqs})
        kinds = [f"{q['request_type'][:3]} {q['entity']} {label(q['record_id']) if q['entity'] != 'Shot' else 'A'}"
                 for q in reqs]
        rows.append(f"  {tag} {kinds} -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    S2 = state(SHOTS)
    picks = []
    for sh, tag in TAGS[:3]:
        wired = {label(rid(d, "task")) for d in S2[sh["id"]]["deps"]} | {label(rid(d, "dependent_task")) for d in S2[sh["id"]]["deps"]}
        picks.append(f"{tag}={'/'.join(sorted(wired & {'xa', 'xb'})) or 'none'}")
    rows.append(f"  wired after batch 1: {' '.join(picks)}")
    for sh, tag in TAGS:
        show(tag, S2[sh["id"]])

    rows.append("\n=== undo batch 2: the snapshot's content, order, desc, dur on every old Task")
    reqs = [upd("Task", i, {k: old[k] for k in KEEP}) for s in SHOTS for i, old in snaps[s["id"]]["tasks"].items()]
    r = c.post("/entity/_batch", json={"requests": reqs})
    rows.append(f"  -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    S3 = state(SHOTS)
    for sh, tag in TAGS:
        show(tag, S3[sh["id"]])
    rows.append("\n=== after vs before the merge")
    for sh, tag in TAGS:
        compare(f"{tag} after undo vs before merge", S0[sh["id"]], S3[sh["id"]])
    compare("negative control, C merged vs C before", S0[C["id"]], S1[C["id"]])
    all_task_ids = [t["id"] for s in (S0, S1, S2) for v in s.values() for t in v["tasks"]]
    tpl_ids = list(idsA.values()) + list(idsB.values())

rows.append("\n=== left clean?")
rows.append(f"  Shots {N}*: {len(T.search(c, 'shots', [['code', 'starts_with', N]], ['code']))}")
rows.append(f"  Tasks {N}* site-wide: {len(T.search(c, 'tasks', [['content', 'starts_with', N]], ['content']))}")
rows.append(f"  Tasks by id seen (Shot and template): "
            f"{len(T.search(c, 'tasks', [['id', 'in', all_task_ids + tpl_ids]], ['content']))}")
rows.append(f"  TaskDependency rows on any of them: {len(T.deps_among(c, all_task_ids + tpl_ids))}")
rows.append(f"  templates {N}*: {len(T.search(c, 'task_templates', [['code', 'starts_with', N]], ['code']))}")
rows.append(f"\nwall {time.monotonic() - T0:.1f}s, {CALLS[0]} calls")

_lib.emit("112_template_unmerge_linked_twice", "\n".join(rows), env)
