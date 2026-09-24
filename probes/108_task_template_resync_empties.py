"""Q: probe 102 found the task_template re-sync overwrites a linked Task's field when T's value is
non-empty and keeps it when T's is empty. Where is the line for the in-between values?

  - a checkbox `milestone` false on T's task vs a linked Task with true
  - a numeric 0 on T's task (`est_in_mins`, `duration`) vs a linked Task with a value
  - a text `sg_description` "" vs null on T's task, the linked Task holding a value
  - `duration` on T's task vs a linked Task with only `start_date` set, and with only `due_date` set
    (102 covered a Task with no dates and one with both)

One template T, no edges (so no dependency cascade moves a date):
  z  milestone False, est 0, description ""          the "falsy but set" case
  n  duration 0, description null, est null          0 duration, null text, null number
  c  milestone True, est 300, description "T.c"      positive control (102: overwritten)
  f  duration 480                                    positive control, a Task with no dates (102)
  s  duration 960                                    Task with start_date only
  d  duration 960                                    Task with due_date only
One Shot created with T, each Task hand-edited away from T, then task_template null, then T (the
recipe 015 re-apply). Each step is read back. Negative control: `n`'s est null keeps the Task's 60.

Preconditions: none from an operator. The probe provisions every row (one template and its 6 tasks,
one Shot and its 6 Tasks) and `_lib.Created` deletes them, failure included.

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
    raise SystemExit("probe 108 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
step = {"type": "Step", "id": ST[sorted(ST)[0]]}
F = ["content", "template_task", "milestone", "est_in_mins", "duration", "sg_description",
     "start_date", "due_date"]
rows = []


def fields(t):
    a = t["attributes"]
    return (f"milestone={a['milestone']!s:<5} est={a['est_in_mins']!s:<4} dur={a['duration']!s:<4} "
            f"desc={a['sg_description']!r:<8} start={a['start_date']} due={a['due_date']}")


def snap(label, shot):
    got = T.tasks_on(c, shot, F)
    T.adopt(made, got)
    rows.append(f"  {label}: {len(got)} Tasks")
    for t in got:
        tt = (T.rel(t, "template_task") or {}).get("id")
        rows.append(f"    {t['attributes']['content']:<2} linked={tt in ids.values()!s:<5} {fields(t)}")
    return {t["attributes"]["content"]: t for t in got}


def put(slug, i, body, label):
    r = c.put(f"/entity/{slug}/{i}", json=body)
    rows.append(f"  {label} -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    return r


with _lib.Created(c) as made:
    TT, ids = T.template(c, made, "zzprobe_108_T", {
        "z": {"step": step, "milestone": False, "est_in_mins": 0, "sg_description": ""},
        "n": {"step": step, "duration": 0, "sg_description": None, "est_in_mins": None},
        "c": {"step": step, "milestone": True, "est_in_mins": 300, "sg_description": "T.c"},
        "f": {"step": step, "duration": 480},
        "s": {"step": step, "duration": 960},
        "d": {"step": step, "duration": 960}})
    rows.append("=== template T, as read")
    for t in sorted(T.search(c, "tasks", [["task_template", "is", TT]], F), key=lambda t: t["id"]):
        rows.append(f"    {t['attributes']['content']:<2} {fields(t)}")

    rows.append("\n=== Shot, created with T, hand-edited")
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_108_sh", "task_template": TT}))
    k = snap("created", sh)
    put("tasks", k["z"]["id"], {"milestone": True, "est_in_mins": 60, "sg_description": "hand"},
        "PUT z milestone True est 60 desc hand")
    put("tasks", k["n"]["id"], {"duration": 1920, "est_in_mins": 60, "sg_description": "hand",
                                "start_date": None, "due_date": None}, "PUT n dur 1920 est 60 desc hand")
    put("tasks", k["c"]["id"], {"milestone": False, "est_in_mins": 60, "sg_description": "hand"},
        "PUT c milestone False est 60 desc hand")
    put("tasks", k["f"]["id"], {"start_date": None, "due_date": None, "duration": 1920},
        "PUT f dates null, dur 1920")
    put("tasks", k["s"]["id"], {"due_date": None, "duration": None}, "PUT s due null dur null")
    put("tasks", k["s"]["id"], {"start_date": "2026-05-04"}, "PUT s start 2026-05-04")
    put("tasks", k["d"]["id"], {"start_date": None, "duration": None}, "PUT d start null dur null")
    put("tasks", k["d"]["id"], {"due_date": "2026-05-08"}, "PUT d due 2026-05-08")
    snap("before", sh)
    put("shots", sh["id"], {"task_template": None}, "PUT Shot task_template null")
    snap("after null", sh)
    put("shots", sh["id"], {"task_template": TT}, "PUT Shot task_template T")
    snap("after T", sh)
    ts = [t["id"] for t in T.tasks_on(c, sh, ["content"])]

rows.append("\n=== left clean?")
for slug, key in (("shots", "code"), ("task_templates", "code")):
    rows.append(f"  {slug} zzprobe_108*: {len(T.search(c, slug, [[key, 'starts_with', 'zzprobe_108']], [key]))}")
rows.append(f"  Tasks on the Shot: {len(T.search(c, 'tasks', [['entity', 'is', sh]], ['content']))}")
rows.append(f"  template tasks: {len(T.search(c, 'tasks', [['id', 'in', list(ids.values())]], ['content']))}")
rows.append(f"  TaskDependency rows on any of them: {len(T.deps_among(c, ts + list(ids.values())))}")
rows.append(f"\n  wall {time.monotonic() - T0:.1f}s, {CALLS[0]} calls")

_lib.emit("108_task_template_resync_empties", "\n".join(rows), env)
