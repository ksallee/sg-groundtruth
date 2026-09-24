"""Q: after clearing a Task's start_date/due_date pins it (finding 093), does `PUT {"pinned": false}`
leave both dates null, or does the server fill them? What does one PUT with the nulls and
`pinned: false` together do? Do downstream Tasks move when an upstream-only Task's dates go null?

093 measured this on a dependent (a Task with an upstream). This probe measures a Task with no
upstream edge at all: one isolated (no edges either way) and one that is only upstream of another,
to see whether "pinned" and "recompute on unpin" mean anything without an upstream to satisfy, and
whether a downstream Task follows a null.

Writes only, in the sandbox, behind --write. Every row is deleted.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

t0 = time.monotonic()
env = _lib.load_env()
c = _lib.client()
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 097 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}

FIELDS = ["content", "start_date", "due_date", "duration", "pinned", "dependency_violation"]


def dep(made, down, up, typ="finish-to-start-next-day"):
    T.post(c, made, "task_dependencies", {"task": {"type": "Task", "id": down},
                                          "dependent_task": {"type": "Task", "id": up}, "dependency_type": typ})


calls = [0]


def count(fn):
    def wrapped(*a, **kw):
        calls[0] += 1
        return fn(*a, **kw)
    return wrapped


with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_097_shot"}))
    calls[0] += 1

    def task(name):
        calls[0] += 1
        return T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_097_{name}",
                                         "start_date": "2026-03-02", "due_date": "2026-03-03"})["id"]

    ids = {n: task(n) for n in ("iso", "root", "down")}
    dep(made, ids["down"], ids["root"])  # root -FS-> down
    calls[0] += 1

    def show(label, names):
        calls[0] += 1
        got = {t["attributes"]["content"][12:]: t["attributes"] for t in
               T.search(c, "tasks", [["id", "in", [ids[n] for n in names]]], FIELDS)}
        rows.append(f"  {label}")
        for n in names:
            a = got[n]
            rows.append(f"    {n:<5} start={a['start_date']!s:<12} due={a['due_date']!s:<12} "
                        f"dur={a['duration']!s:<6} pinned={a['pinned']!s:<5} violation={a['dependency_violation']}")

    def put(who, body, note):
        calls[0] += 1
        r = c.put(f"/entity/tasks/{ids[who]}", json=body)
        rows.append(f"\n  PUT {who} {body} -> {r.status_code} {T.errs(r) if not r.ok else ''}  # {note}")

    rows.append("=== isolated Task, no edges at all ===")
    show("iso created 03-02..03-03, no deps", ["iso"])

    put("iso", {"start_date": None, "due_date": None}, "clear both dates on an unlinked Task")
    show("after clear", ["iso"])

    put("iso", {"pinned": False}, "unpin, nothing to recompute from")
    show("after unpin (separate PUT)", ["iso"])

    put("iso", {"start_date": None, "due_date": None, "pinned": False}, "nulls + pinned:false in ONE put")
    show("after combined put", ["iso"])

    rows.append("\n=== root Task: no upstream, is upstream of 'down' (root -FS-> down) ===")
    show("root+down created 03-02..03-03, linked, down unpinned", ["root", "down"])

    put("root", {"start_date": None, "due_date": None}, "clear root's dates (root has no upstream itself)")
    show("after clear: does down follow a null upstream?", ["root", "down"])

    put("root", {"pinned": False}, "unpin root, nothing upstream of root to recompute from")
    show("after unpin (separate PUT): does root refill? does down move again?", ["root", "down"])

    put("root", {"start_date": None, "due_date": None, "pinned": False}, "nulls + pinned:false in ONE put")
    show("after combined put on root: what wins, does down move?", ["root", "down"])

rows.append("\n=== left clean?")
calls[0] += 1
rows.append(f"  sandbox Tasks zzprobe_097*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_097']], ['content']))}")
rows.append(f"\n  calls: {calls[0]}  wall: {time.monotonic() - t0:.1f}s")

_lib.emit("097_null_dates_unpin", "\n".join(rows), env)
