"""Q: does clearing `start_date` and `due_date` on a Task (writing both to null) pin it?

`entity_types/Task` and probe 087 found that writing a dependent's own dates pins it: any date PUT
sets `pinned` true, which then holds the Task against an upstream write, and `PUT {"pinned": false}`
reschedules it at once. A sync that clears dates to let the server recompute them needs to know
whether a null write counts as "writing its own dates" the same way a real date does, whether one
date alone is enough, and whether `duration` survives the clear.

Five dependents of one upstream `up`, each written once, then `up` moved later:
  both   start_date and due_date null
  start  start_date null only
  due    due_date null only
  sreal  a real start_date only (control)
  dreal  a real due_date only (control)
Then the in-run control on `due` itself: a real due_date, read pinned; a real start_date, read
pinned. Last, `pinned: false` on every dependent.

Preconditions: none from an operator. The probe provisions every row it reads (1 Shot, 6 Tasks,
5 TaskDependency rows) and `_lib.Created` deletes them, failure included.

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

# Count calls without touching _lib (#76 owns that): wrap this client's request.
CALLS = [0]
_request = c.request


def counted(method, path, **kw):
    CALLS[0] += 1
    return _request(method, path, **kw)


c.request = counted
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 093 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}

FIELDS = ["content", "start_date", "due_date", "duration", "pinned", "dependency_violation"]
NAMES = ("up", "both", "start", "due", "sreal", "dreal")

with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_093_shot"}))
    ids = {n: T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_093_{n}",
                                        "start_date": "2026-03-02", "due_date": "2026-03-03"})["id"]
           for n in NAMES}
    for n in NAMES[1:]:
        # `task` is the downstream, `dependent_task` the upstream it waits on (087).
        T.post(c, made, "task_dependencies", {"task": {"type": "Task", "id": ids[n]},
                                              "dependent_task": {"type": "Task", "id": ids["up"]},
                                              "dependency_type": "finish-to-start-next-day"})

    def show(label):
        got = {t["attributes"]["content"][12:]: t["attributes"] for t in
               T.search(c, "tasks", [["id", "in", list(ids.values())]], FIELDS)}
        rows.append(f"  {label}")
        for n in NAMES:
            a = got[n]
            rows.append(f"    {n:<5} start={a['start_date']!s:<10} due={a['due_date']!s:<10} "
                        f"dur={a['duration']!s:<4} pinned={a['pinned']!s:<5} violation={a['dependency_violation']}")

    def put(who, body, note=""):
        r = c.put(f"/entity/tasks/{ids[who]}", json=body)
        rows.append(f"  PUT {who} {body} -> {r.status_code} {T.errs(r) if not r.ok else ''} {note}".rstrip())

    show("linked: up -FS-> each dependent, all created 03-02..03-03")

    rows.append("")
    put("both", {"start_date": None, "due_date": None})
    put("start", {"start_date": None})
    put("due", {"due_date": None})
    put("sreal", {"start_date": "2026-03-05"}, "# control: a real start_date")
    put("dreal", {"due_date": "2026-03-06"}, "# control: a real due_date")
    show("after one write on each dependent")

    rows.append("")
    put("up", {"start_date": "2026-03-09", "due_date": "2026-03-10"}, "# upstream moved later")
    show("after the upstream write: who follows?")

    rows.append("")
    put("due", {"due_date": "2026-03-20"}, "# control on the same Task: a real due_date")
    show("after")

    rows.append("")
    put("due", {"start_date": "2026-03-16"}, "# control on the same Task: a real start_date")
    show("after")

    rows.append("")
    for n in NAMES[1:]:
        put(n, {"pinned": False})
    show("after unpinning each")

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_093*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_093']], ['content']))}")
rows.append(f"  TaskDependency rows on those Task ids: {len(T.deps_among(c, list(ids.values())))}")

rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")
_lib.emit("093_clear_dates_pin", "\n".join(rows), env)
