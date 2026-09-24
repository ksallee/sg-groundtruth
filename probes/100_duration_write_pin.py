"""Q: does writing `duration` on a dependent Task pin it, the way a date write does (087, 093)? What
happens to its start_date and due_date, and does it still follow the upstream afterwards? Separately,
does writing `duration` on the upstream Task move its downstream Tasks, the way a date write does?

`entity_types/Task` and probe 087 covered date writes on a dependent and on the upstream end.
Probe 093 covered clearing (nulling) a dependent's dates. Neither wrote `duration` alone on either end.

Writes only, in the sandbox, behind --write. Every row is deleted.
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

# Count calls without touching _lib (#76 owns that): wrap this client's request.
CALLS = [0]
_request = c.request


def counted(method, path, **kw):
    CALLS[0] += 1
    return _request(method, path, **kw)


c.request = counted  # every call, Created's deletes included, goes through c.request
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 100 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}


def dep(made, down, up, typ="finish-to-start-next-day"):
    T.post(c, made, "task_dependencies", {"task": {"type": "Task", "id": down},
                                          "dependent_task": {"type": "Task", "id": up}, "dependency_type": typ})


with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_100_shot"}))

    def task(name):
        return T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_100_{name}",
                                         "start_date": "2026-03-02", "due_date": "2026-03-03"})["id"]

    # up -> down -> down2, a plain finish-to-start chain; solo has no edge (the unlinked control)
    ids = {n: task(n) for n in ("up", "down", "down2", "solo")}
    dep(made, ids["down"], ids["up"])
    dep(made, ids["down2"], ids["down"])
    deps = [i for slug, i in made.rows if slug == "task_dependencies"]

    def show(label):
        got = {t["attributes"]["content"][12:]: t["attributes"] for t in
               T.search(c, "tasks", [["id", "in", list(ids.values())]],
                        ["content", "start_date", "due_date", "duration", "pinned", "dependency_violation"])}
        rows.append(f"  {label}")
        for n in ids:
            a = got[n]
            rows.append(f"    {n:<6} {a['start_date']}..{a['due_date']} dur={a['duration']:<5} "
                        f"pinned={a['pinned']!s:<5} violation={a['dependency_violation']}")

    show("linked: up -FS-> down -FS-> down2, solo unlinked, all written 03-02..03-03 (dur=960)")

    # 0. Control: duration alone on a Task with no edges. What does an unlinked Task do?
    r = c.put(f"/entity/tasks/{ids['solo']}", json={"duration": 1920})
    rows.append(f"\n  PUT solo duration=1920 (no edges) -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    show("after")

    # 1. Write duration alone on the dependent. Does it pin? What happens to its dates?
    r = c.put(f"/entity/tasks/{ids['down']}", json={"duration": 1920})
    rows.append(f"\n  PUT down duration=1920 (dates untouched) -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    show("after")

    # 2. Move the upstream. Does the now-duration-written down still follow it?
    r = c.put(f"/entity/tasks/{ids['up']}", json={"due_date": "2026-03-10"})
    rows.append(f"\n  PUT up due_date=2026-03-10 (later) -> {r.status_code}")
    show("after")

    # 3. Unpin down, see if it recomputes back onto the upstream.
    r = c.put(f"/entity/tasks/{ids['down']}", json={"pinned": False})
    rows.append(f"\n  PUT down pinned=false -> {r.status_code}")
    show("after")

    # 4. Now the control: write duration on the UPSTREAM end. Does down (unpinned) move?
    r = c.put(f"/entity/tasks/{ids['up']}", json={"duration": 2880})
    rows.append(f"\n  PUT up duration=2880 (upstream, down unpinned) -> {r.status_code}")
    show("after")

    # 5. Positive control: a date write on the dependent, same run. Does it pin?
    r = c.put(f"/entity/tasks/{ids['down']}", json={"start_date": "2026-03-20"})
    rows.append(f"\n  PUT down start_date=2026-03-20 (date write, positive control) -> {r.status_code}")
    show("after")

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_100*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_100']], ['content']))}")
rows.append(f"  Shots zzprobe_100*: "
            f"{len(T.search(c, 'shots', [['project', 'is', P], ['code', 'starts_with', 'zzprobe_100']], ['code']))}")
rows.append(f"  live TaskDependency rows {deps}: {len(T.search(c, 'task_dependencies', [['id', 'in', deps]], ['id']))}")

rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")
_lib.emit("100_duration_write_pin", "\n".join(rows), env)
