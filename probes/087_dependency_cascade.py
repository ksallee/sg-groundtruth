"""Q: when an upstream Task's dates move, which downstream Tasks move with it, and does `pinned` stop it?

`entity_types/Task` found that a date write on a dependent Task sets `pinned` and can raise
`dependency_violation`. A sync app that rewrites dates on template-generated Tasks needs the other
direction: what a write on the upstream end does to a chain, pinned and unpinned, later and earlier.

Writes only, in the sandbox, behind --write. Every row is deleted.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

env = _lib.load_env()
c = _lib.client()
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 087 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}


def dep(made, down, up, typ="finish-to-start-next-day"):
    T.post(c, made, "task_dependencies", {"task": {"type": "Task", "id": down},
                                          "dependent_task": {"type": "Task", "id": up}, "dependency_type": typ})


with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_087_shot"}))

    def task(name):
        return T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_087_{name}",
                                         "start_date": "2026-03-02", "due_date": "2026-03-03"})["id"]

    # up -> d1 -> d2, and up -> pin, and up -> ss (start-to-start)
    ids = {n: task(n) for n in ("up", "d1", "d2", "pin", "ss")}
    dep(made, ids["d1"], ids["up"])
    dep(made, ids["d2"], ids["d1"])
    dep(made, ids["pin"], ids["up"])
    dep(made, ids["ss"], ids["up"], "start-to-start")

    def show(label):
        got = {t["attributes"]["content"][12:]: t["attributes"] for t in
               T.search(c, "tasks", [["id", "in", list(ids.values())]],
                        ["content", "start_date", "due_date", "pinned", "dependency_violation"])}
        rows.append(f"  {label}")
        for n in ids:
            a = got[n]
            rows.append(f"    {n:<4} {a['start_date']}..{a['due_date']} pinned={a['pinned']!s:<5} "
                        f"violation={a['dependency_violation']}")

    show("linked: up -FS-> d1 -FS-> d2, up -FS-> pin, up -SS-> ss")
    r = c.put(f"/entity/tasks/{ids['pin']}", json={"pinned": True})
    rows.append(f"\n  PUT pin pinned=true -> {r.status_code} {T.errs(r) if not r.ok else ''}")

    for label, body in (("PUT up due_date 2026-03-05 (later)", {"due_date": "2026-03-05"}),
                        ("PUT up due_date 2026-03-02 (earlier)", {"due_date": "2026-03-02"}),
                        ("PUT up start_date 2026-03-09 (whole task later)", {"start_date": "2026-03-09"}),
                        ("PUT up duration 2400", {"duration": 2400})):
        r = c.put(f"/entity/tasks/{ids['up']}", json=body)
        rows.append(f"\n  {label} -> {r.status_code} {T.errs(r) if not r.ok else ''}")
        show("after")

    r = c.put(f"/entity/tasks/{ids['d1']}", json={"start_date": "2026-03-02", "due_date": "2026-03-03"})
    rows.append(f"\n  PUT d1 dates before up ends -> {r.status_code}")
    show("after")
    r = c.put(f"/entity/tasks/{ids['d1']}", json={"pinned": False})
    rows.append(f"\n  PUT d1 pinned=false -> {r.status_code}")
    show("after")
    r = c.put(f"/entity/tasks/{ids['up']}", json={"due_date": "2026-03-20"})
    rows.append(f"\n  PUT up due_date 2026-03-20 -> {r.status_code}")
    show("after")

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_087*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_087']], ['content']))}")

_lib.emit("087_dependency_cascade", "\n".join(rows), env)
