"""Q: does a `delete` request inside `POST /entity/_batch` retire the row the same way
`DELETE /entity/<type>/<id>` does, so that revive brings it back with the same id, fields and links?

Measured for a Task (with a linked Version and a dependency edge, as probe 089) and for a
TaskDependency (with a type and offset, as probe 095). Each row goes through both routes in turn:
batch `delete`, read back, revive, read back; then the plain `DELETE` as the control, on the same row.
Negative control: a live row put in the same `return_only: retired` reads must not be listed.

Preconditions: none from an operator. The probe provisions 1 Shot, 3 Tasks, 2 edges and 1 Version in
the sandbox and `_lib.Created` deletes them, failure included.

Writes only, in the sandbox, behind --write. Budget 60 s; wall time and call count are printed.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

if not _lib.writes_allowed():
    raise SystemExit("probe 103 writes; run with --write")
T0 = time.monotonic()
env = _lib.load_env()
c = _lib.client()

# Count calls without touching _lib (#76 owns that). Created's deletes go through c.request too.
CALLS = [0]
_request = c.request


def counted(method, path, **kw):
    CALLS[0] += 1
    return _request(method, path, **kw)


c.request = counted
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
rows = []
TASK_F = ["content", "entity", "project", "start_date", "due_date", "sg_description", "sg_status_list",
          "upstream_tasks", "downstream_tasks"]
DEP_F = ["task", "dependent_task", "dependency_type", "offset_days"]


def tref(i):
    return {"type": "Task", "id": i}


def snap(slug, i, fields):
    """A comparable read of one live row: attributes and link ids. None when GET is not 200."""
    r = c.get(f"/entity/{slug}/{i}", params={"fields": ",".join(fields)})
    if not r.ok:
        return r.status_code, None
    d = r.json()["data"]
    out = {k: d["attributes"].get(k) for k in fields if k in (d.get("attributes") or {})}
    for k in fields:
        v = T.rel(d, k)
        if k in (d.get("relationships") or {}):
            out[k] = sorted(x["id"] for x in v) if isinstance(v, list) else (v or {}).get("id")
    return 200, out


def retired(slug, ids):
    """Which of `ids` read back under return_only retired, by _search and by GET options."""
    r = c.post(f"/entity/{slug}/_search", headers=T.ARR,
               json={"filters": [["id", "in", ids]], "fields": ["id"], "options": {"return_only": "retired"}})
    found = sorted(x["id"] for x in r.json()["data"]) if r.ok else T.errs(r)
    gets = {i: c.get(f"/entity/{slug}/{i}", params={"options[return_only]": "retired"}).status_code for i in ids}
    return found, gets


def revive(slug, i):
    r = c.post(f"/entity/{slug}/{i}", params={"revive": 1})
    return f"{r.status_code} {json.dumps(r.json().get('meta')) if r.ok else T.errs(r)}"


with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_103_shot"}))
    ids = {n: T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_103_{n}",
                                        "start_date": "2026-03-02", "due_date": "2026-03-03",
                                        "sg_description": f"desc {n}"})["id"]
           for n in ("a", "b", "c")}
    A, B, C = (tref(ids[n]) for n in "abc")
    e_ba = T.post(c, made, "task_dependencies", {"task": B, "dependent_task": A})["id"]
    e_ca = T.post(c, made, "task_dependencies", {"task": C, "dependent_task": A,
                                                 "dependency_type": "start-to-start", "offset_days": 2})["id"]
    ver = T.post(c, made, "versions", {"project": P, "code": "zzprobe_103_v001", "entity": sh, "sg_task": B})["id"]
    rows.append(f"=== a={ids['a']} b={ids['b']} c={ids['c']}; edge b on a row {e_ba} (default type), "
                f"edge c on a row {e_ca} start-to-start +2; Version {ver} sg_task=b")

    def task_state(label):
        st, b = snap("tasks", ids["b"], TASK_F)
        _, a = snap("tasks", ids["a"], TASK_F)
        est, e = snap("task_dependencies", e_ba, DEP_F)
        _, v = snap("versions", ver, ["sg_task"])
        found, gets = retired("tasks", [ids["b"], ids["a"]])
        efound, _ = retired("task_dependencies", [e_ba])
        rows.append(f"  {label}")
        rows.append(f"    b GET {st} {json.dumps(b) if b else ''}")
        rows.append(f"    a downstream_tasks={a['downstream_tasks']}  edge b-on-a GET {est}  Version.sg_task={v['sg_task']}")
        rows.append(f"    retired tasks [b, a]: _search={found} GET={gets}   retired edge b-on-a _search={efound}")
        return b, e

    def dep_state(label):
        st, e = snap("task_dependencies", e_ca, DEP_F)
        _, cc = snap("tasks", ids["c"], TASK_F)
        found, gets = retired("task_dependencies", [e_ca, e_ba])
        rows.append(f"  {label}")
        rows.append(f"    edge c-on-a GET {st} {json.dumps(e) if e else ''}  c upstream_tasks={cc['upstream_tasks']}")
        rows.append(f"    retired edges [c-on-a, b-on-a]: _search={found} GET={gets}")
        return e

    def batch_delete(entity, i):
        r = c.post("/entity/_batch", json={"requests": [{"request_type": "delete", "entity": entity, "record_id": i}]})
        return f"{r.status_code} {json.dumps(r.json().get('data')) if r.ok else T.errs(r)}"

    rows.append("\n=== Task b")
    before, e_before = task_state("before")
    for route in ("batch", "DELETE"):
        if route == "batch":
            rows.append(f"  _batch delete Task b -> {batch_delete('Task', ids['b'])}")
        else:
            r = c.delete(f"/entity/tasks/{ids['b']}")
            rows.append(f"  DELETE /entity/tasks/b -> {r.status_code} {len(r.content)} bytes")
        task_state(f"after {route}")
        rows.append(f"  revive b -> {revive('tasks', ids['b'])}")
        after, e_after = task_state(f"after revive ({route})")
        rows.append(f"    b fields same as before: {after == before}; edge b-on-a same: {e_after == e_before}")

    rows.append("\n=== TaskDependency c on a")
    dbefore = dep_state("before")
    for route in ("batch", "DELETE"):
        if route == "batch":
            rows.append(f"  _batch delete TaskDependency -> {batch_delete('TaskDependency', e_ca)}")
        else:
            r = c.delete(f"/entity/task_dependencies/{e_ca}")
            rows.append(f"  DELETE /entity/task_dependencies/{e_ca} -> {r.status_code} {len(r.content)} bytes")
        dep_state(f"after {route}")
        rows.append(f"  revive edge -> {revive('task_dependencies', e_ca)}")
        dafter = dep_state(f"after revive ({route})")
        rows.append(f"    edge fields same as before: {dafter == dbefore}")

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_103*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_103']], ['content']))}"
            f"  Shots: {len(T.search(c, 'shots', [['project', 'is', P], ['code', 'starts_with', 'zzprobe_103']], ['code']))}"
            f"  Versions: {len(T.search(c, 'versions', [['project', 'is', P], ['code', 'starts_with', 'zzprobe_103']], ['code']))}"
            f"  TaskDependency rows on a, b, c: "
            f"{len(T.search(c, 'task_dependencies', [['task', 'in', [A, B, C]]], ['task']))}")
rows.append(f"\n=== run: {time.monotonic() - T0:.1f}s wall, {CALLS[0]} calls")

_lib.emit("103_batch_delete_revive", "\n".join(rows), env)
