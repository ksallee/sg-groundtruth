"""Q: does clearing `start_date` and `due_date` on a Task (writing both to null) pin it?

`entity_types/Task` and probe 087 found that writing a dependent's own dates pins it: any date PUT
sets `pinned` true, which then holds the Task against an upstream write, and `PUT {"pinned": false}`
reschedules it at once. A sync that clears dates to let the server recompute them needs to know
whether a null write counts as "writing its own dates" the same way a real date does, whether one
date alone is enough, and whether `duration` survives the clear.

Writes only, in the sandbox, behind --write. Every row is deleted.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

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
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 093 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}

FIELDS = ["content", "start_date", "due_date", "duration", "pinned", "dependency_violation"]


def dep(made, down, up, typ="finish-to-start-next-day"):
    T.post(c, made, "task_dependencies", {"task": {"type": "Task", "id": down},
                                          "dependent_task": {"type": "Task", "id": up}, "dependency_type": typ})


with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_093_shot"}))

    def task(name):
        return T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_093_{name}",
                                         "start_date": "2026-03-02", "due_date": "2026-03-03"})["id"]

    ids = {n: task(n) for n in ("up", "down")}
    dep(made, ids["down"], ids["up"])

    def show(label):
        got = {t["attributes"]["content"][12:]: t["attributes"] for t in
               T.search(c, "tasks", [["id", "in", list(ids.values())]], FIELDS)}
        rows.append(f"  {label}")
        for n in ids:
            a = got[n]
            rows.append(f"    {n:<5} start={a['start_date']!s:<12} due={a['due_date']!s:<12} "
                        f"dur={a['duration']!s:<6} pinned={a['pinned']!s:<5} violation={a['dependency_violation']}")

    def put(who, body, note):
        r = c.put(f"/entity/tasks/{ids[who]}", json=body)
        rows.append(f"\n  PUT {who} {body} -> {r.status_code} {T.errs(r) if not r.ok else ''}  # {note}")

    show("linked: up -FS-> down, both created 03-02..03-03, down unpinned")

    put("down", {"start_date": None, "due_date": None}, "clear both dates, down starts unpinned")
    show("after")

    put("up", {"start_date": "2026-03-09", "due_date": "2026-03-10"}, "upstream moved, whole task later")
    show("after: does the cleared/pinned down follow?")

    put("down", {"pinned": False}, "unpin the cleared down")
    show("after: does unpinning recompute the null dates?")

    put("down", {"start_date": None}, "clear start_date only, down unpinned again")
    show("after")

    put("up", {"due_date": "2026-03-16"}, "upstream moved again")
    show("after: does down (start cleared only) follow?")

    put("down", {"pinned": False}, "unpin down again")
    show("after: recompute?")

    put("down", {"due_date": None}, "clear due_date only, down unpinned again")
    show("after")

    put("up", {"start_date": "2026-03-20"}, "upstream moved a third time")
    show("after: does down (due cleared only) follow?")

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_093*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_093']], ['content']))}")

rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")
_lib.emit("093_clear_dates_pin", "\n".join(rows), env)
