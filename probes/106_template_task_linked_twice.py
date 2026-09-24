"""Q: two Tasks on one Shot both point `template_task` at the same template task X (a conflict loser
left linked). When the Shot's `task_template` is written (null, then T; recipes 015 and 020), does the
apply re-sync both Tasks' fields (probe 102), create anything, and which of the two gets T's edges to
X's neighbours: both, one (lowest id? oldest?), or none? Does anything error?

Template T: w, x, y on three steps; edges x on w and y on x (both finish-to-start-next-day), so X has
an upstream and a downstream neighbour. X carries est_in_mins 600 and a description.

Shot 1: xa then xb, both created with template_task = X, content xa/xb, est 60, description "hand".
        xa has the lower id and is the older.
Shot 2: the same, but the lower-id Task gets a later-sorting content and the higher-id one an earlier
        `created_at` (settable on create, probe 070): separates lowest id from oldest and from name.
Shot 3: positive control, one Task linked to X, the same hand values.
Shot 4: xa, xb linked to X, w and y Tasks linked to T.w, T.y, and the edges y on xb, xb on w
        made by hand beforehand: does the apply keep, move or duplicate them?
Each Shot: read, PUT task_template null, read, PUT task_template T, read.

Preconditions: none from an operator. The probe provisions every row it reads (1 template, 4 Shots,
9 hand-made Tasks, 2 edges) and `_lib.Created` deletes them, failure included.

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
if not _lib.writes_allowed():
    raise SystemExit("probe 106 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
sw, sx, sy = ({"type": "Step", "id": ST[k]} for k in sorted(ST)[:3])
rows = []
names = {}
dep_ids = set()
F = ["content", "template_task", "est_in_mins", "sg_description", "created_at"]


def nm(r):
    return names.get(r["id"], f"#{r['id']}") if r else None


def snap(label, shot, made):
    got = T.tasks_on(c, shot, F)
    T.adopt(made, got)
    for t in got:
        names.setdefault(t["id"], t["attributes"]["content"].replace("zzprobe_106_", "") + "(new)")
    deps = T.deps_among(c, [t["id"] for t in got])
    dep_ids.update(d["id"] for d in deps)
    rows.append(f"  {label}: {len(got)} Tasks, {len(deps)} deps")
    for t in got:
        a = t["attributes"]
        tt = T.rel(t, "template_task")
        rows.append(f"    {names[t['id']]:<8} id+{t['id'] - BASE:<3} content={a['content'].replace('zzprobe_106_', '')}"
                    f" template_task={nm(tt) if tt else None} est={a['est_in_mins']} desc={a['sg_description']}"
                    f" created={a['created_at'][:10]}")
    for d in deps:
        a = d["attributes"]
        rows.append(f"    dep id+{d['id'] - DBASE}: {nm(T.rel(d, 'task'))} on {nm(T.rel(d, 'dependent_task'))} {a['dependency_type']}")
    return got, deps


with _lib.Created(c) as made:
    TT, tids = T.template(
        c, made, "zzprobe_106_tt",
        {"zzprobe_106_w": {"step": sw},
         "zzprobe_106_x": {"step": sx, "est_in_mins": 600, "sg_description": "T.x"},
         "zzprobe_106_y": {"step": sy}},
        [("zzprobe_106_x", "zzprobe_106_w", {"dependency_type": "finish-to-start-next-day"}),
         ("zzprobe_106_y", "zzprobe_106_x", {"dependency_type": "finish-to-start-next-day"})])
    for k, v in tids.items():
        names[v] = "T." + k.replace("zzprobe_106_", "")
    BASE = min(tids.values())
    tdeps = T.deps_among(c, list(tids.values()))
    dep_ids.update(d["id"] for d in tdeps)
    DBASE = min(d["id"] for d in tdeps)
    X = {"type": "Task", "id": tids["zzprobe_106_x"]}
    rows.append("T: w, x (est 600, desc T.x), y; x on w, y on x finish-to-start-next-day")

    def shot(code):
        return T.ref(T.post(c, made, "shots", {"project": P, "code": code}))

    def linked(sh, label, content, extra=None):
        body = {"project": P, "entity": sh, "content": f"zzprobe_106_{content}", "step": sx,
                "template_task": X, "est_in_mins": 60, "sg_description": "hand", **(extra or {})}
        r = c.post("/entity/tasks", json=body)
        shown = {k: v for k, v in (extra or {}).items() if k not in ("step", "template_task")}
        rows.append(f"  POST Task {label} template_task={names[body['template_task']['id']]} {shown or ''} -> {r.status_code} "
                    f"{T.errs(r) if not r.ok else ''}")
        if not r.ok:
            raise SystemExit("\n".join(rows))
        i = made.add("tasks", r.json()["data"]["id"])
        names[i] = label
        return i

    def apply(sh):
        for v, lab in ((None, "null"), (TT, "T")):
            r = c.put(f"/entity/shots/{sh['id']}", json={"task_template": v})
            rows.append(f"  PUT task_template {lab} -> {r.status_code} {T.errs(r) if not r.ok else ''}")
            snap(f"after {lab}", sh, made)

    rows.append("\n=== Shot 1: xa (lower id, older), xb, both linked to T.x")
    sh1 = shot("zzprobe_106_shot1")
    linked(sh1, "xa", "x_a")
    linked(sh1, "xb", "x_b")
    snap("before", sh1, made)
    apply(sh1)

    rows.append("\n=== Shot 2: xa (lower id, content x_z), xb (higher id, created_at 2020, content x_a)")
    sh2 = shot("zzprobe_106_shot2")
    linked(sh2, "xa", "x_z")
    linked(sh2, "xb", "x_a", {"created_at": "2020-01-01T00:00:00Z"})
    snap("before", sh2, made)
    apply(sh2)

    rows.append("\n=== Shot 3: control, one Task x1 linked to T.x")
    sh3 = shot("zzprobe_106_shot3")
    linked(sh3, "x1", "x")
    snap("before", sh3, made)
    apply(sh3)

    rows.append("\n=== Shot 4: xa, xb linked to T.x; w, y linked; the edges pre-made on xb, the higher id")
    sh4 = shot("zzprobe_106_shot4")
    xa4 = linked(sh4, "xa", "x_a")
    xb4 = linked(sh4, "xb", "x_b")
    w4 = linked(sh4, "w", "w", {"step": sw, "template_task": {"type": "Task", "id": tids["zzprobe_106_w"]}})
    y4 = linked(sh4, "y", "y", {"step": sy, "template_task": {"type": "Task", "id": tids["zzprobe_106_y"]}})
    for down, up in ((y4, xb4), (xb4, w4)):
        T.post(c, made, "task_dependencies", {"task": {"type": "Task", "id": down},
                                              "dependent_task": {"type": "Task", "id": up},
                                              "dependency_type": "finish-to-start-next-day"})
    snap("before", sh4, made)
    apply(sh4)

rows.append("\n=== left clean?")
rows.append(f"  Tasks zzprobe_106* (site-wide, template tasks included): "
            f"{len(T.search(c, 'tasks', [['content', 'starts_with', 'zzprobe_106']], ['content']))}")
for slug, key in (("shots", "code"), ("task_templates", "code")):
    rows.append(f"  {slug} zzprobe_106*: {len(T.search(c, slug, [[key, 'starts_with', 'zzprobe_106']], [key]))}")
all_deps = sorted(dep_ids)
live = T.search(c, "task_dependencies", [["id", "in", all_deps]], ["id"]) if all_deps else []
rows.append(f"  TaskDependency rows seen this run still live: {len(live)} of {len(all_deps)}")
rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")

_lib.emit("106_template_task_linked_twice", "\n".join(rows), env)
